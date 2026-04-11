from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from core.inference.model_router import ModelSelection, ReasoningModelRouter
from core.inference.residency import ResidencyMonitor, ResidencySnapshot
from router.dispatch_core import TOOL_REGISTRY


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AGENT_LOG_PATH = ROOT / "temp" / "logs" / "agent_reasoning.jsonl"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class InferenceRequest:
    prompt: str
    model_path: str | Path | None = None
    max_tokens: int = 192
    temperature: float = 0.2
    top_p: float = 0.9
    context_window: int = 4096
    threads: int = 4
    gpu_layers: int = 0
    task_complexity: str = "complex"


@dataclass(frozen=True)
class InferenceResult:
    text: str
    fallback_reason: str | None = None
    model_path: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class InferenceManager:
    def __init__(
        self,
        *,
        router: ReasoningModelRouter | None = None,
        residency_monitor: ResidencyMonitor | None = None,
        telemetry_enabled: bool | None = None,
        telemetry_path: Path | None = None,
    ) -> None:
        self.router = router or ReasoningModelRouter.from_env()
        self.residency_monitor = residency_monitor or ResidencyMonitor.from_env()
        self.telemetry_enabled = (
            _env_bool("AI_LAN_REASONING_TELEMETRY_ENABLED", False)
            if telemetry_enabled is None
            else telemetry_enabled
        )
        configured_log_path = os.getenv("AI_LAN_AGENT_LOG_PATH", "").strip()
        self.telemetry_path = telemetry_path or (
            Path(configured_log_path) if configured_log_path else DEFAULT_AGENT_LOG_PATH
        )
        self._llm: Any | None = None
        self._loaded_model_path: Path | None = None

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, object] | None:
        normalized = text.strip()
        if not normalized:
            return None
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

    @staticmethod
    def _extract_trigger_payload(buffer: str) -> tuple[dict[str, object] | None, str | None]:
        payload = InferenceManager._extract_json_object(buffer)
        if isinstance(payload, dict) and str(payload.get("mode", "")).strip().lower() == "action":
            return payload, "json_action"

        action_match = re.search(r"(?:^|\n)Action:\s*([a-z0-9_.-]+)", buffer, flags=re.IGNORECASE)
        if not action_match:
            return None, None
        action_name = action_match.group(1).strip().lower()
        spec = TOOL_REGISTRY.get(action_name)
        if spec is None:
            return None, None

        args: dict[str, object] = {}
        args_match = re.search(r"(?:^|\n)Args:\s*(\{.*?\})(?:\n|$)", buffer, flags=re.IGNORECASE | re.DOTALL)
        if args_match:
            try:
                parsed = json.loads(args_match.group(1))
                if isinstance(parsed, dict):
                    args = parsed
            except json.JSONDecodeError:
                args = {}
        if spec.required_args and any(name not in args for name in spec.required_args):
            return None, None

        thought_match = re.search(r"(?:^|\n)Thought:\s*(.+)", buffer, flags=re.IGNORECASE)
        safety_match = re.search(r"(?:^|\n)Safety(?:_level)?:\s*(low|medium|high)", buffer, flags=re.IGNORECASE)
        payload = {
            "mode": "action",
            "thought": thought_match.group(1).strip() if thought_match else f"Execute {action_name}",
            "action": action_name,
            "args": args,
            "safety_level": safety_match.group(1).strip().lower() if safety_match else "low",
        }
        return payload, "text_action"

    def _stream_generation(self, runtime: Any, request: InferenceRequest) -> tuple[str, bool, dict[str, object] | None, str | None]:
        trigger_enabled = _env_bool("AI_LAN_STREAM_TOOL_TRIGGER_ENABLED", True)
        trigger_pattern = os.getenv("AI_LAN_STREAM_TOOL_TRIGGER_PATTERN", "Action:").strip()
        buffer = ""
        intercepted = False
        trigger_payload: dict[str, object] | None = None
        trigger_mode: str | None = None
        stream = runtime(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=["\n\nUser:", "\n\nSYSTEM:"],
            stream=True,
        )
        if isinstance(stream, dict):
            choices = stream.get("choices", [])
            if choices:
                buffer = str(choices[0].get("text", ""))
            return buffer, False, None, None
        for chunk in stream:
            piece = ""
            if isinstance(chunk, dict):
                choices = chunk.get("choices", [])
                if choices:
                    piece = str(choices[0].get("text", ""))
            elif isinstance(chunk, str):
                piece = chunk
            buffer += piece
            if not trigger_enabled:
                continue
            payload, payload_mode = self._extract_trigger_payload(buffer)
            if payload is not None:
                intercepted = True
                trigger_payload = payload
                trigger_mode = payload_mode
                break
            if trigger_pattern and trigger_pattern in buffer:
                trigger_mode = "text_trigger_seen"
        return buffer, intercepted, trigger_payload, trigger_mode

    def unload(self, *, reason: str) -> None:
        self._llm = None
        self._loaded_model_path = None
        self._write_telemetry({"event": "llama_unload", "reason": reason})

    def _write_telemetry(self, payload: dict[str, object]) -> None:
        if not self.telemetry_enabled:
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _load_llama_class(self) -> type[Any]:
        from llama_cpp import Llama  # type: ignore[import-untyped]

        return Llama

    def _build_runtime(
        self,
        *,
        model_path: Path,
        request: InferenceRequest,
    ) -> Any:
        llama_class = self._load_llama_class()
        return llama_class(
            model_path=str(model_path),
            n_ctx=request.context_window,
            n_threads=request.threads,
            n_gpu_layers=request.gpu_layers,
            verbose=False,
        )

    def _get_runtime(
        self,
        *,
        model_path: Path,
        request: InferenceRequest,
        resident_enabled: bool,
    ) -> tuple[Any | None, str | None]:
        if resident_enabled and self._llm is not None and self._loaded_model_path == model_path:
            return self._llm, None

        if resident_enabled and self._llm is not None and self._loaded_model_path != model_path:
            self.unload(reason="model_switch")

        try:
            runtime = self._build_runtime(model_path=model_path, request=request)
        except Exception:
            return None, "llama_runtime_unavailable"

        if resident_enabled:
            self._llm = runtime
            self._loaded_model_path = model_path

        return runtime, None

    @staticmethod
    def _build_metadata(
        *,
        selection_reason: str,
        task_complexity: str,
        residency_snapshot: ResidencySnapshot,
        resident_enabled: bool,
    ) -> dict[str, object]:
        metadata: dict[str, object] = {
            "selection_reason": selection_reason,
            "task_complexity": task_complexity,
            "resident_enabled": resident_enabled,
        }
        if residency_snapshot.host_ram_percent is not None:
            metadata["host_ram_percent"] = round(residency_snapshot.host_ram_percent, 2)
        if residency_snapshot.reason is not None:
            metadata["residency_probe_reason"] = residency_snapshot.reason
        return metadata

    def _attempt_model_generation(
        self,
        *,
        selection: ModelSelection,
        request: InferenceRequest,
        metadata: dict[str, object],
    ) -> InferenceResult:
        if selection.model_path is None:
            return InferenceResult(
                text="",
                fallback_reason="llama_model_not_configured",
                metadata=metadata,
            )

        if not selection.model_path.exists():
            return InferenceResult(
                text="",
                fallback_reason="llama_model_missing",
                model_path=str(selection.model_path),
                metadata=metadata,
            )

        runtime, runtime_error = self._get_runtime(
            model_path=selection.model_path,
            request=request,
            resident_enabled=selection.resident_enabled,
        )
        if runtime is None:
            return InferenceResult(
                text="",
                fallback_reason=runtime_error or "llama_runtime_unavailable",
                model_path=str(selection.model_path),
                metadata=metadata,
            )

        try:
            output, intercepted, trigger_payload, trigger_mode = self._stream_generation(runtime, request)
        except Exception:
            if selection.resident_enabled:
                self.unload(reason="runtime_error")
            return InferenceResult(
                text="",
                fallback_reason="llama_runtime_error",
                model_path=str(selection.model_path),
                metadata=metadata,
            )

        text = str(output).strip()
        if not text:
            return InferenceResult(
                text="",
                fallback_reason="llama_empty_response",
                model_path=str(selection.model_path),
                metadata=metadata,
            )

        success_metadata = dict(metadata)
        success_metadata["effective_backend"] = "llama_cpp"
        success_metadata["stream_intercepted"] = intercepted
        if trigger_payload is not None:
            success_metadata["stream_trigger_payload"] = trigger_payload
        if trigger_mode is not None:
            success_metadata["stream_trigger_mode"] = trigger_mode
        self._write_telemetry(
            {
                "event": "llama_success",
                "model_path": str(selection.model_path),
                "resident_enabled": selection.resident_enabled,
                "task_complexity": selection.task_complexity,
                "stream_intercepted": intercepted,
                "stream_trigger_mode": trigger_mode,
                "selection_reason": selection.selection_reason,
            }
        )
        return InferenceResult(
            text=text,
            fallback_reason=None,
            model_path=str(selection.model_path),
            metadata=success_metadata,
        )

    @sentinel
    def generate(self, request: InferenceRequest) -> InferenceResult:
        snapshot = self.residency_monitor.sample()
        routing_plan = self.router.build_plan(
            requested_model_path=request.model_path,
            task_complexity=request.task_complexity,
            pressure_high=snapshot.pressure_high,
        )
        selection = routing_plan.primary
        metadata = self._build_metadata(
            selection_reason=selection.selection_reason,
            task_complexity=selection.task_complexity,
            residency_snapshot=snapshot,
            resident_enabled=selection.resident_enabled,
        )
        metadata["routing_candidate_paths"] = [
            str(candidate.model_path) if candidate.model_path is not None else ""
            for candidate in routing_plan.candidates
        ]
        metadata["routing_candidate_reasons"] = [
            candidate.selection_reason for candidate in routing_plan.candidates
        ]

        if snapshot.pressure_high and len(routing_plan.candidates) == 1:
            metadata["effective_backend"] = "classic"
            metadata["fallback_reason"] = "llama_residency_unloaded_high_pressure"
            self._write_telemetry({"event": "llama_fallback", **metadata})
            return InferenceResult(
                text="",
                fallback_reason="llama_residency_unloaded_high_pressure",
                model_path=str(selection.model_path) if selection.model_path else None,
                metadata=metadata,
            )

        if selection.resident_enabled and snapshot.pressure_high:
            self.unload(reason="high_memory_pressure")
        attempted: list[dict[str, object]] = []
        for candidate in routing_plan.candidates:
            candidate_metadata = dict(metadata)
            candidate_metadata["selection_reason"] = candidate.selection_reason
            candidate_metadata["resident_enabled"] = candidate.resident_enabled
            attempt = self._attempt_model_generation(
                selection=candidate,
                request=request,
                metadata=candidate_metadata,
            )
            if attempt.fallback_reason is None:
                success_metadata = dict(attempt.metadata)
                success_metadata["routing_attempts"] = attempted
                if len(attempted) > 0:
                    success_metadata["routing_fallback_applied"] = True
                return InferenceResult(
                    text=attempt.text,
                    fallback_reason=None,
                    model_path=attempt.model_path,
                    metadata=success_metadata,
                )

            attempted.append(
                {
                    "model_path": attempt.model_path or "",
                    "selection_reason": candidate.selection_reason,
                    "fallback_reason": attempt.fallback_reason,
                }
            )

        metadata["effective_backend"] = "classic"
        metadata["fallback_reason"] = attempted[-1]["fallback_reason"] if attempted else "llama_model_not_configured"
        metadata["routing_attempts"] = attempted
        metadata["routing_fallback_applied"] = len(attempted) > 1
        self._write_telemetry(
            {
                "event": "llama_fallback",
                "fallback_reason": metadata["fallback_reason"],
                "routing_attempts": attempted,
                **{key: value for key, value in metadata.items() if key not in {"routing_attempts"}},
            }
        )
        return InferenceResult(
            text="",
            fallback_reason=str(metadata["fallback_reason"]),
            model_path=str(selection.model_path) if selection.model_path else None,
            metadata=metadata,
        )


_DEFAULT_MANAGER: InferenceManager | None = None


def get_default_inference_manager() -> InferenceManager:
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = InferenceManager()
    return _DEFAULT_MANAGER


def reset_default_inference_manager() -> None:
    global _DEFAULT_MANAGER
    _DEFAULT_MANAGER = None


__all__ = [
    "InferenceManager",
    "InferenceRequest",
    "InferenceResult",
    "get_default_inference_manager",
    "reset_default_inference_manager",
]