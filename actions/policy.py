"""Compatibility shim for legacy imports. Use safety.policy_engine instead."""

from safety.policy_engine import (
    ALLOWED_ACTIONS,
    CONFIRMATION_REQUIRED_ACTIONS,
    DENIED_ACTIONS,
    PolicyDecision,
    evaluate_action_policy,
)

__all__ = [
    "PolicyDecision",
    "evaluate_action_policy",
    "ALLOWED_ACTIONS",
    "DENIED_ACTIONS",
    "CONFIRMATION_REQUIRED_ACTIONS",
]
