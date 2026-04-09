"""Main Thought -> Action -> Observation runtime for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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

    def run_step(
        self, payload: str | dict[str, object], *, confirmed: bool = False
    ) -> ReactStepResult:
        action: AgentAction = parse_agent_action(payload)
        self.state.thoughts.append(action.thought)
        self.buffer.add(role="assistant_thought", message=action.thought)

        try:
            result = parse_and_dispatch(action.to_dict(), confirmed=confirmed)
        except Exception:
            # Fallback to direct router dispatch if parse_and_dispatch fails unexpectedly.
            result = dispatch_action(action.to_dict(), confirmed=confirmed)
        observation_text = str(result.get("observation") or result.get("policy_reason") or "")
        self.state.observations.append(observation_text)
        self.buffer.add(role="tool_observation", message=observation_text)

        return ReactStepResult(request=action.to_dict(), result=result, state=self.state)


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
