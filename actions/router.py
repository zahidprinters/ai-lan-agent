"""Compatibility shim for legacy imports. Use router.dispatch_core instead."""

from router.dispatch_core import (
    ActionExecutionResult,
    ToolSpec,
    TOOL_REGISTRY,
    append_action_audit_log,
    dispatch_agent_action,
    validate_action_args,
)
from tools.web_search import search_web

__all__ = [
    "ToolSpec",
    "TOOL_REGISTRY",
    "search_web",
    "ActionExecutionResult",
    "validate_action_args",
    "append_action_audit_log",
    "dispatch_agent_action",
]
