"""Main Thought -> Action -> Observation runtime for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from agents.react.controller import action_signature
from agents.react.reflection import evaluate_reflection_policy
from agents.react.structured_logging import append_structured_log
from agents.react.tool_risk import get_tool_risk_profile
from agents.react.state import ReactState
from memory.short_term.buffer import ShortTermBuffer
from router.router import dispatch_action, parse_and_dispatch
from router.schema import AgentAction, parse_agent_action


@dataclass
class ReactStepResult:
    request: dict[str, object]
    result: dict[str, Any]
    state: ReactState


class ReactAgent:
    """Lightweight ReAct runtime that preserves state across steps."""

    def __init__(self, buffer_max_items: int = 40) -> None:
        self.state = ReactState()
        self.buffer = ShortTermBuffer(max_items=buffer_max_items)
        self.max_reflection_retries_per_step = max(0, int(os.getenv("AI_LAN_REFLECTION_RETRIES", "1")))
        self.max_reflection_retries_per_turn = max(
            0, int(os.getenv("AI_LAN_REFLECTION_RETRIES_PER_TURN", "3"))
        )

    def run_step(
        self,
        payload: str | dict[str, object],
        *,
        confirmed: bool = False,
        policy_context: dict[str, Any] | None = None,
    ) -> ReactStepResult:
        initial_action: AgentAction = parse_agent_action(payload)
        self.state.thoughts.append(initial_action.thought)
        self.buffer.add(role="assistant_thought", message=initial_action.thought)

        current_payload = initial_action.to_dict()
        result: dict[str, Any] = {}
        retries_for_step = 0
        seen_signatures: set[str] = {action_signature(current_payload)}
        reflection_notes: list[str] = []

        append_structured_log(
            "agent",
            {
                "event": "react_step_start",
                "action": initial_action.action,
                "thought": initial_action.thought,
                "safety_level": initial_action.safety_level,
                "risk_profile": get_tool_risk_profile(initial_action.action).to_dict(),
            },
        )

        while True:
            try:
                append_structured_log(
                    "tool",
                    {
                        "event": "tool_dispatch_attempt",
                        "action": str(current_payload.get("action", "")),
                        "args": dict(current_payload.get("args", {})) if isinstance(current_payload.get("args"), dict) else {},
                        "confirmed": confirmed,
                        "risk_profile": get_tool_risk_profile(str(current_payload.get("action", ""))).to_dict(),
                    },
                )
                result = parse_and_dispatch(
                    current_payload,
                    confirmed=confirmed,
                    policy_context=policy_context,
                )
            except Exception as exc:
                append_structured_log(
                    "error",
                    {
                        "event": "tool_dispatch_exception",
                        "action": str(current_payload.get("action", "")),
                        "error": str(exc),
                        "risk_profile": get_tool_risk_profile(str(current_payload.get("action", ""))).to_dict(),
                    },
                )
                # Fallback to direct router dispatch if parse_and_dispatch fails unexpectedly.
                result = dispatch_action(
                    current_payload,
                    confirmed=confirmed,
                    policy_context=policy_context,
                )

            append_structured_log(
                "tool",
                {
                    "event": "tool_dispatch_result",
                    "action": str(result.get("action", current_payload.get("action", ""))),
                    "status": str(result.get("status", "unknown")),
                    "policy_reason": str(result.get("policy_reason", "")),
                    "risk_profile": get_tool_risk_profile(str(result.get("action", current_payload.get("action", "")))).to_dict(),
                },
            )

            decision = evaluate_reflection_policy(
                action_payload=current_payload,
                result=result,
                retry_index=retries_for_step + 1,
                retries_for_step=retries_for_step,
                retries_for_turn=self.state.reflection_retries_used,
                max_reflection_retries_per_step=self.max_reflection_retries_per_step,
                max_reflection_retries_per_turn=self.max_reflection_retries_per_turn,
                confirmed=confirmed,
            )
            reflection_notes.append(decision.note)
            append_structured_log(
                "agent",
                {
                    "event": "reflection_decision",
                    "action": str(current_payload.get("action", "")),
                    "decision": decision.reason,
                    "retry_allowed": decision.retry_allowed,
                    "note": decision.note,
                    "risk_profile": get_tool_risk_profile(str(current_payload.get("action", ""))).to_dict(),
                },
            )
            if not decision.retry_allowed:
                result.setdefault("reflection_skipped_reason", decision.reason)
                break

            reflected_payload = decision.next_payload
            if reflected_payload is None:
                result.setdefault("reflection_skipped_reason", decision.reason)
                break
            reflected_signature = action_signature(reflected_payload)
            if reflected_signature in seen_signatures:
                result.setdefault("reflection_skipped_reason", "repeated_action_suppressed")
                break

            seen_signatures.add(reflected_signature)
            retries_for_step += 1
            self.state.reflection_retries_used += 1
            current_payload = reflected_payload

            reflected_thought = str(reflected_payload.get("thought", "")).strip()
            if reflected_thought:
                self.state.thoughts.append(reflected_thought)
                self.buffer.add(role="assistant_thought", message=reflected_thought)

        result["reflection_retry_count"] = retries_for_step
        if retries_for_step > 0:
            result["reflection_applied"] = True
        result["reflection_notes"] = reflection_notes

        observation_text = str(result.get("observation") or result.get("policy_reason") or "")
        self.state.observations.append(observation_text)
        self.buffer.add(role="tool_observation", message=observation_text)
        append_structured_log(
            "agent",
            {
                "event": "react_step_complete",
                "action": str(result.get("action", current_payload.get("action", ""))),
                "status": str(result.get("status", "unknown")),
                "reflection_retry_count": retries_for_step,
                "risk_profile": get_tool_risk_profile(str(result.get("action", current_payload.get("action", "")))).to_dict(),
            },
        )

        return ReactStepResult(request=current_payload, result=result, state=self.state)


def run_react_step(
    payload: str | dict[str, object],
    *,
    confirmed: bool = False,
    policy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stateless helper for single-step execution."""
    agent = ReactAgent()
    step_result = agent.run_step(payload, confirmed=confirmed, policy_context=policy_context)
    return {
        "request": step_result.request,
        "result": step_result.result,
        "state": {
            "thoughts": list(step_result.state.thoughts),
            "observations": list(step_result.state.observations),
        },
    }
