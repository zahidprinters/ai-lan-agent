"""Router facade to dispatch validated actions."""

from __future__ import annotations

import logging
from typing import Any, Callable

from router.dispatch_core import (
    ActionExecutionResult,
    append_action_audit_log,
    dispatch_agent_action,
    validate_action_args,
)
from router.schema import AgentAction, parse_agent_action
from safety.policy_engine import evaluate_policy
from tools.system.clipboard import read_clipboard
from tools.system.files import list_workspace_files
from tools.web.search import run_search

LOGGER = logging.getLogger(__name__)

LAYERED_TOOL_HANDLERS: dict[str, Callable[..., Any]] = {
    "web.search": run_search,
    "pc.read_clipboard": read_clipboard,
    "pc.list_workspace_files": list_workspace_files,
}


def _dispatch_layered_action(action: AgentAction, *, confirmed: bool = False) -> dict[str, Any]:
    decision = evaluate_policy(action)
    if not decision.allowed:
        result = ActionExecutionResult(
            status="rejected",
            action=action.action,
            observation=None,
            policy_reason=decision.reason,
        )
        append_action_audit_log(action, result)
        return result.to_dict()

    validate_action_args(action)

    if decision.requires_confirmation and not confirmed:
        result = ActionExecutionResult(
            status="confirmation_required",
            action=action.action,
            observation=None,
            policy_reason=decision.reason,
        )
        append_action_audit_log(action, result)
        return result.to_dict()

    handler = LAYERED_TOOL_HANDLERS[action.action]
    observation = handler(**action.args)
    result = ActionExecutionResult(
        status="executed",
        action=action.action,
        observation=observation,
        policy_reason=decision.reason,
    )
    append_action_audit_log(action, result)
    return result.to_dict()


def dispatch_action(
    payload: str | dict[str, object] | AgentAction,
    *,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Dispatches an action payload and returns a plain dictionary result."""
    action = payload if isinstance(payload, AgentAction) else parse_agent_action(payload)

    if action.action in LAYERED_TOOL_HANDLERS:
        try:
            return _dispatch_layered_action(action, confirmed=confirmed)
        except Exception:
            # Fallback to proven legacy path if layered handling fails unexpectedly.
            LOGGER.exception(
                "Layered dispatch failed for %s; falling back to legacy dispatcher.", action.action
            )
            result = dispatch_agent_action(action, confirmed=confirmed)
            return result.to_dict()

    result = dispatch_agent_action(action, confirmed=confirmed)
    return result.to_dict()


def parse_and_dispatch(
    payload: str | dict[str, object], *, confirmed: bool = False
) -> dict[str, Any]:
    """Parses payload into validated schema before dispatch."""
    action = parse_agent_action(payload)
    return dispatch_action(action, confirmed=confirmed)


__all__ = ["dispatch_action", "parse_and_dispatch", "dispatch_agent_action"]
