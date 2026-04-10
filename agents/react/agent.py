"""Main Thought -> Action -> Observation runtime for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from agents.react.controller import action_signature, build_reflection_payload, is_reflection_candidate
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
        self, payload: str | dict[str, object], *, confirmed: bool = False
    ) -> ReactStepResult:
        initial_action: AgentAction = parse_agent_action(payload)
        self.state.thoughts.append(initial_action.thought)
        self.buffer.add(role="assistant_thought", message=initial_action.thought)

        current_payload = initial_action.to_dict()
        result: dict[str, Any] = {}
        retries_for_step = 0
        seen_signatures: set[str] = {action_signature(current_payload)}

        while True:
            try:
                result = parse_and_dispatch(current_payload, confirmed=confirmed)
            except Exception:
                # Fallback to direct router dispatch if parse_and_dispatch fails unexpectedly.
                result = dispatch_action(current_payload, confirmed=confirmed)

            can_retry = (
                not confirmed
                and retries_for_step < self.max_reflection_retries_per_step
                and self.state.reflection_retries_used < self.max_reflection_retries_per_turn
                and is_reflection_candidate(current_payload, result)
            )
            if not can_retry:
                if (
                    not confirmed
                    and is_reflection_candidate(current_payload, result)
                    and self.state.reflection_retries_used >= self.max_reflection_retries_per_turn
                ):
                    result.setdefault("reflection_skipped_reason", "retry_budget_exhausted")
                break

            reflected_payload = build_reflection_payload(
                current_payload,
                result,
                retry_index=retries_for_step + 1,
            )
            if reflected_payload is None:
                result.setdefault("reflection_skipped_reason", "no_recovery_candidate")
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

        observation_text = str(result.get("observation") or result.get("policy_reason") or "")
        self.state.observations.append(observation_text)
        self.buffer.add(role="tool_observation", message=observation_text)

        return ReactStepResult(request=current_payload, result=result, state=self.state)


def run_react_step(payload: str | dict[str, object], *, confirmed: bool = False) -> dict[str, Any]:
    """Stateless helper for single-step execution."""
    agent = ReactAgent()
    step_result = agent.run_step(payload, confirmed=confirmed)
    return {
        "request": step_result.request,
        "result": step_result.result,
        "state": {
            "thoughts": list(step_result.state.thoughts),
            "observations": list(step_result.state.observations),
        },
    }
