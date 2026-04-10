"""Router facade to dispatch validated actions."""

from __future__ import annotations

from typing import Any

from router.dispatch_core import dispatch_agent_action
from router.schema import AgentAction, parse_agent_action


def dispatch_action(
    payload: str | dict[str, object] | AgentAction,
    *,
    confirmed: bool = False,
    policy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatches an action payload and returns a plain dictionary result."""
    action = payload if isinstance(payload, AgentAction) else parse_agent_action(payload)
    return dispatch_agent_action(
        action,
        confirmed=confirmed,
        policy_context=policy_context,
    ).to_dict()


def parse_and_dispatch(
    payload: str | dict[str, object],
    *,
    confirmed: bool = False,
    policy_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parses payload into validated schema before dispatch."""
    action = parse_agent_action(payload)
    return dispatch_action(action, confirmed=confirmed, policy_context=policy_context)


__all__ = ["dispatch_action", "parse_and_dispatch", "dispatch_agent_action"]
