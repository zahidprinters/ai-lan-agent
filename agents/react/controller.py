from __future__ import annotations

"""Local neural planner that turns context into either a tool action or a reply."""

import json
import re
import os
from dataclasses import asdict, dataclass, replace
from typing import Any, Callable

from agents.react.planner import build_plan_requirements, validate_or_repair_plan
from agents.react.runtime_guard import build_execution_contract, evaluate_runtime_dispatch_guard
from agents.react.tool_risk import get_tool_risk_profile
from agents.react.prompt import build_react_prompt
from agents.react.tool_schema import build_model_tool_schema
from core.inference.generate import generate_text
from core.inference.local_reasoning import generate_structured_response_result
from router.dispatch_core import TOOL_REGISTRY
from router.schema import ActionSchemaError, parse_agent_action

DEFAULT_TOOL_NAMES = tuple(sorted(TOOL_REGISTRY))
DEFAULT_TOOL_SCHEMA = tuple(item.name for item in build_model_tool_schema())
FAILED_TOOL_STATUSES = frozenset({"failed", "blocked", "blocked_policy", "adb_unavailable"})


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class PlannedTurn:
    mode: str
    source: str
    action_payload: dict[str, object] | None = None
    reply_text: str | None = None
    raw_text: str = ""
    metadata: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _action_signature(action_payload: dict[str, object] | None) -> str:
    if not action_payload:
        return ""
    return json.dumps(action_payload, ensure_ascii=True, sort_keys=True)


def action_signature(action_payload: dict[str, object] | None) -> str:
    """Public wrapper used by the runtime for repeated-action suppression."""
    return _action_signature(action_payload)


def _is_empty_observation(observation: object) -> bool:
    if observation is None:
        return True
    if isinstance(observation, str):
        return not observation.strip()
    if isinstance(observation, (list, tuple, dict, set)):
        return len(observation) == 0
    return False


def infer_task_complexity(
    *,
    message: str,
    runtime_context: dict[str, Any] | None = None,
    recent_observations: list[str] | None = None,
) -> str:
    if not _env_flag("AI_LAN_REASONING_DYNAMIC_PLANNING", default=True):
        return "complex"

    lowered = message.strip().lower()
    word_count = len(lowered.split())
    has_context = bool(runtime_context and runtime_context.get("assembled_context"))
    has_observations = bool(recent_observations)
    complex_markers = (
        "because",
        "compare",
        "summarize",
        "analyze",
        "reflect",
        "policy",
        "history",
        "latest",
    )
    if has_context or has_observations or word_count > 10 or any(marker in lowered for marker in complex_markers):
        return "complex"
    return "simple"


def is_reflection_candidate(
    action_payload: dict[str, object], result: dict[str, Any]
) -> bool:
    status = str(result.get("status", "")).strip().lower()
    if status in FAILED_TOOL_STATUSES:
        return True

    # Some tool adapters return success with no observation payload.
    if status == "executed" and _is_empty_observation(result.get("observation")):
        action_name = str(action_payload.get("action", "")).strip().lower()
        return action_name in {
            "web.search",
            "memory.search",
            "pc.list_workspace_files",
            "context.build",
        }
    return False


def build_reflection_payload(
    action_payload: dict[str, object], result: dict[str, Any], *, retry_index: int
) -> dict[str, object] | None:
    """Build a deterministic one-step recovery payload for recoverable failures."""
    if retry_index > 1:
        return None

    args_obj = action_payload.get("args")
    args = dict(args_obj) if isinstance(args_obj, dict) else {}
    adjusted = False

    query = args.get("query")
    if isinstance(query, str) and query.strip():
        query_text = query.strip()
        if "fallback" not in query_text.lower():
            args["query"] = f"{query_text} fallback"
            adjusted = True

    if not adjusted:
        return None

    original_thought = str(action_payload.get("thought", "")).strip() or "Retry action"
    status = str(result.get("status", "unknown")).strip().lower()
    reflected = {
        "thought": f"{original_thought} | reflection retry after {status}",
        "action": action_payload.get("action", ""),
        "args": args,
        "safety_level": action_payload.get("safety_level", "low"),
    }

    try:
        return parse_agent_action(reflected).to_dict()
    except ActionSchemaError:
        return None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    normalized = text.strip()
    if not normalized:
        return None

    if normalized.startswith("```"):
        lines = [line for line in normalized.splitlines() if not line.startswith("```")]
        normalized = "\n".join(lines).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(normalized):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(normalized[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _extract_action_payload(candidate: dict[str, Any]) -> dict[str, object] | None:
    if "payload" in candidate and isinstance(candidate["payload"], dict):
        candidate = candidate["payload"]

    filtered = {
        key: candidate[key]
        for key in ("thought", "action", "args", "safety_level")
        if key in candidate
    }
    if len(filtered) != 4:
        return None

    try:
        action = parse_agent_action(filtered)
    except ActionSchemaError:
        return None
    return action.to_dict()


def _extract_plan_steps(candidate: dict[str, Any]) -> list[str]:
    raw_plan = candidate.get("plan")
    if not isinstance(raw_plan, list):
        return []
    steps = [str(item).strip() for item in raw_plan if str(item).strip()]
    return steps[:5]


def _parse_stream_trigger_payload(payload: dict[str, object]) -> dict[str, object] | None:
    try:
        return parse_agent_action(payload).to_dict()
    except ActionSchemaError:
        return None


def _extract_text_action_payload(raw_text: str) -> dict[str, object] | None:
    action_match = re.search(r"(?:^|\n)Action:\s*([a-z0-9_.-]+)", raw_text, flags=re.IGNORECASE)
    if not action_match:
        return None
    action_name = action_match.group(1).strip().lower()
    thought_match = re.search(r"(?:^|\n)Thought:\s*(.+)", raw_text, flags=re.IGNORECASE)
    safety_match = re.search(r"(?:^|\n)Safety(?:_level)?:\s*(low|medium|high)", raw_text, flags=re.IGNORECASE)
    args_match = re.search(r"(?:^|\n)Args:\s*(\{.*?\})(?:\n|$)", raw_text, flags=re.IGNORECASE | re.DOTALL)
    args: dict[str, object] = {}
    if args_match:
        try:
            parsed_args = json.loads(args_match.group(1))
            if isinstance(parsed_args, dict):
                args = parsed_args
        except json.JSONDecodeError:
            args = {}
    spec = TOOL_REGISTRY.get(action_name)
    if spec is None:
        return None
    if spec.required_args and any(name not in args for name in spec.required_args):
        return None
    payload = {
        "thought": thought_match.group(1).strip() if thought_match else f"Execute {action_name}",
        "action": action_name,
        "args": args,
        "safety_level": safety_match.group(1).strip().lower() if safety_match else "low",
    }
    return _parse_stream_trigger_payload(payload)


class NeuralActionController:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        generation_length: int = 120,
        reasoning_backend: str | None = None,
    ) -> None:
        self.enabled = (
            _env_flag("AI_LAN_NEURAL_CONTROLLER", default=True) if enabled is None else enabled
        )
        self.generation_length = generation_length
        self.reasoning_backend = (
            (reasoning_backend or os.getenv("AI_LAN_REASONING_BACKEND", "classic"))
            .strip()
            .lower()
        )

    def _parse_output(self, raw_text: str) -> PlannedTurn | None:
        payload = _extract_json_object(raw_text)
        if payload is None:
            text_action = _extract_text_action_payload(raw_text)
            if text_action is not None:
                risk_profile = get_tool_risk_profile(str(text_action.get("action", "")))
                return PlannedTurn(
                    mode="action",
                    source="model_stream_trigger",
                    action_payload=text_action,
                    raw_text=raw_text.strip(),
                    metadata={
                        "plan_steps": [],
                        "stream_trigger_mode": "text_action",
                        "risk_profile": risk_profile.to_dict(),
                    },
                )
            return None

        mode = str(payload.get("mode", "")).strip().lower()
        if mode not in {"reply", "action"}:
            text_action = _extract_text_action_payload(raw_text)
            if text_action is not None:
                risk_profile = get_tool_risk_profile(str(text_action.get("action", "")))
                return PlannedTurn(
                    mode="action",
                    source="model_stream_trigger",
                    action_payload=text_action,
                    raw_text=raw_text.strip(),
                    metadata={
                        "plan_steps": [],
                        "stream_trigger_mode": "text_action",
                        "risk_profile": risk_profile.to_dict(),
                    },
                )
            return None

        plan_steps = _extract_plan_steps(payload)
        metadata = {"plan_steps": plan_steps} if plan_steps else None
        if mode == "reply":
            response = payload.get("response") or payload.get("reply") or payload.get("text")
            if isinstance(response, str) and response.strip():
                return PlannedTurn(
                    mode="reply",
                    source="model",
                    reply_text=response.strip(),
                    raw_text=raw_text.strip(),
                    metadata=metadata,
                )
            return None

        action_payload = _extract_action_payload(payload)
        if action_payload is not None:
            return PlannedTurn(
                mode="action",
                source="model",
                action_payload=action_payload,
                raw_text=raw_text.strip(),
                metadata=metadata,
            )

        response = payload.get("response") or payload.get("reply")
        if isinstance(response, str) and response.strip():
            return PlannedTurn(
                mode="reply",
                source="model",
                reply_text=response.strip(),
                raw_text=raw_text.strip(),
                metadata=metadata,
            )

        return None

    def plan(
        self,
        *,
        message: str,
        runtime_context: dict[str, Any] | None = None,
        recent_turns: list[dict[str, str]] | None = None,
        recent_thoughts: list[str] | None = None,
        recent_observations: list[str] | None = None,
        tool_names: list[str] | tuple[str, ...] | None = None,
    ) -> PlannedTurn | None:
        if not self.enabled:
            return None

        task_complexity = infer_task_complexity(
            message=message,
            runtime_context=runtime_context,
            recent_observations=recent_observations,
        )
        plan_requirements = build_plan_requirements(
            message=message,
            task_complexity=task_complexity,
            runtime_context=runtime_context,
        )

        prompt = build_react_prompt(
            message=message,
            runtime_context=runtime_context,
            recent_turns=recent_turns,
            recent_thoughts=recent_thoughts,
            recent_observations=recent_observations,
            tool_names=tool_names or DEFAULT_TOOL_SCHEMA or DEFAULT_TOOL_NAMES,
            plan_requirements=plan_requirements.quality_checks,
        )
        generated = ""
        fallback_reason: str | None = None
        local_metadata: dict[str, object] = {}
        if self.reasoning_backend == "llama_cpp":
            local_result = generate_structured_response_result(
                prompt=prompt,
                model_path=os.getenv("AI_LAN_LLAMACPP_MODEL_PATH", "").strip() or None,
                max_tokens=self.generation_length,
                temperature=0.2,
                top_p=0.9,
                context_window=int(os.getenv("AI_LAN_LLAMACPP_CTX", "4096")),
                threads=int(os.getenv("AI_LAN_LLAMACPP_THREADS", "4")),
                gpu_layers=int(os.getenv("AI_LAN_LLAMACPP_GPU_LAYERS", "0")),
                task_complexity=task_complexity,
            )
            generated = local_result.text
            fallback_reason = local_result.fallback_reason
            local_metadata = dict(getattr(local_result, "metadata", None) or {})

        # Deterministic fallback preserves existing behavior when local brain is unavailable.
        if not generated.strip():
            generated = generate_text(
                prompt, length=self.generation_length, temperature=0.2, top_k=20, top_p=0.9
            )
            if self.reasoning_backend == "llama_cpp":
                fallback_reason = fallback_reason or "llama_cpp_empty_response"
        if not generated.strip():
            return None
        parsed_turn = self._parse_output(generated)
        if parsed_turn is not None:
            validation = validate_or_repair_plan(
                candidate_steps=list((parsed_turn.metadata or {}).get("plan_steps", [])) if parsed_turn.metadata else [],
                message=message,
                task_complexity=task_complexity,
                runtime_context=runtime_context,
                action_payload=parsed_turn.action_payload,
                requirements=plan_requirements,
            )
            parsed_turn = replace(
                parsed_turn,
                metadata={
                    **(parsed_turn.metadata or {}),
                    "plan_steps": validation.steps,
                    "plan_validation": {
                        "valid": validation.valid,
                        "source": validation.source,
                        "reasons": validation.reasons,
                    },
                    "plan_requirements": plan_requirements.quality_checks,
                    "risk_profile": validation.risk_profile.to_dict() if validation.risk_profile else None,
                },
            )
        if (
            parsed_turn is not None
            and self.reasoning_backend == "llama_cpp"
        ):
            merged_metadata = {
                "reasoning_backend": "llama_cpp",
                "plan_requirements": plan_requirements.quality_checks,
                "task_complexity": task_complexity,
                **(parsed_turn.metadata or {}),
                **local_metadata,
            }
            if fallback_reason is not None:
                merged_metadata["effective_backend"] = "classic"
                merged_metadata["fallback_reason"] = fallback_reason
            elif "effective_backend" not in merged_metadata:
                merged_metadata["effective_backend"] = "llama_cpp"
            return replace(parsed_turn, metadata=merged_metadata)
        if parsed_turn is not None and self.reasoning_backend != "llama_cpp":
            merged_metadata = {
                "reasoning_backend": self.reasoning_backend,
                "plan_requirements": plan_requirements.quality_checks,
                "task_complexity": task_complexity,
                **(parsed_turn.metadata or {}),
            }
            return replace(parsed_turn, metadata=merged_metadata)
        return parsed_turn

    def plan_iterative(
        self,
        *,
        message: str,
        max_steps: int = 5,
        runtime_context: dict[str, Any] | None = None,
        recent_turns: list[dict[str, str]] | None = None,
        recent_thoughts: list[str] | None = None,
        recent_observations: list[str] | None = None,
        tool_names: list[str] | tuple[str, ...] | None = None,
        observe_action: Callable[[PlannedTurn], str] | None = None,
    ) -> list[PlannedTurn]:
        """Run a bounded ReAct loop until a reply is produced or guardrails stop planning."""
        if not self.enabled:
            return []

        results: list[PlannedTurn] = []
        thoughts: list[str] = list(recent_thoughts or [])[-8:]
        observations: list[str] = list(recent_observations or [])[-8:]
        seen_actions: set[str] = set()

        for _ in range(max_steps):
            turn = self.plan(
                message=message,
                runtime_context=runtime_context,
                recent_turns=recent_turns,
                recent_thoughts=thoughts,
                recent_observations=observations,
                tool_names=tool_names,
            )

            if turn is None:
                break

            if turn.mode == "reply":
                results.append(turn)
                break

            if turn.mode == "action" and turn.action_payload:
                signature = _action_signature(turn.action_payload)
                if signature in seen_actions:
                    break
                seen_actions.add(signature)

                runtime_guard = evaluate_runtime_dispatch_guard(
                    action_payload=turn.action_payload,
                    metadata=turn.metadata,
                )
                merged_turn_metadata = {
                    **(turn.metadata or {}),
                    "runtime_guard": runtime_guard.to_dict(),
                    "execution_contract": build_execution_contract(
                        action_payload=turn.action_payload,
                        metadata={
                            **(turn.metadata or {}),
                            "runtime_guard": runtime_guard.to_dict(),
                        },
                        runtime_guard=runtime_guard,
                    ),
                }
                turn = replace(turn, metadata=merged_turn_metadata)

                if not runtime_guard.allowed:
                    results.append(
                        PlannedTurn(
                            mode="reply",
                            source="runtime_guard",
                            reply_text=(
                                "I cannot dispatch that action because runtime safety "
                                "alignment checks failed."
                            ),
                            raw_text=turn.raw_text,
                            metadata=merged_turn_metadata,
                        )
                    )
                    break

                results.append(turn)
                thoughts.append(str(turn.action_payload.get("thought", "")))

                if observe_action is not None:
                    observation = observe_action(turn).strip() or "(no observation)"
                    observations.append(observation)
                continue

            break

        return results


__all__ = [
    "FAILED_TOOL_STATUSES",
    "NeuralActionController",
    "PlannedTurn",
    "action_signature",
    "build_reflection_payload",
    "infer_task_complexity",
    "is_reflection_candidate",
]
