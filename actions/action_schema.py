"""Compatibility shim for legacy imports. Use router.schema instead."""

from router.schema import ActionSchemaError, AgentAction, parse_agent_action

__all__ = ["AgentAction", "ActionSchemaError", "parse_agent_action"]
