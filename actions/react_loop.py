# actions/react_loop.py
# Copyright (c) 2026 Nadeem Abbas
"""ReAct loop controller for AI Lan Phase 4 routing."""

from debug_utils import sentinel

from router.router import dispatch_action


@sentinel
def orchestrate_react_step(thought: str, action: str) -> str:
    payload: dict[str, object] = {
        "thought": thought,
        "action": action,
        "args": {},
        "safety_level": "low",
    }
    result = dispatch_action(payload)
    return str(result.get("observation") or result.get("policy_reason") or "")


@sentinel
def orchestrate_react_payload(
    action_payload: str | dict[str, object], confirmed: bool = False
) -> dict[str, object]:
    return dispatch_action(action_payload, confirmed=confirmed)


if __name__ == "__main__":
    print("AI Lan ReAct Action Controller Initialized (Phase 4.0 Preview)")
