"""Policy engine facade."""

from __future__ import annotations

from dataclasses import dataclass

from debug_utils import sentinel

from router.schema import AgentAction, parse_agent_action


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


CONFIRMATION_REQUIRED_ACTIONS = {
    "pc.type_text",
    "pc.open_app",
    "android.launch_app",
    "android.tap",
    "android.swipe",
    "android.capture_screenshot",
}
DENIED_ACTIONS = {"pc.execute_shell", "pc.move_mouse"}
ALLOWED_ACTIONS = {
    "web.search",
    "memory.search",
    "context.build",
    "pc.get_system_status",
    "pc.list_running_apps",
    "pc.list_workspace_files",
    "pc.read_clipboard",
    "pc.type_text",
    "pc.open_app",
    "android.list_devices",
    "android.launch_app",
    "android.tap",
    "android.swipe",
    "android.capture_screenshot",
}


@sentinel
def evaluate_action_policy(action: AgentAction) -> PolicyDecision:
    if action.action in DENIED_ACTIONS:
        return PolicyDecision(
            allowed=False,
            reason=f"Action '{action.action}' is disabled until higher-risk controls are implemented.",
        )

    if action.action not in ALLOWED_ACTIONS:
        return PolicyDecision(
            allowed=False,
            reason=f"Action '{action.action}' is not on the current Phase 4 allowlist.",
        )

    if action.action == "web.search" and action.safety_level == "high":
        return PolicyDecision(
            allowed=False,
            reason="web.search cannot be requested with high safety level.",
        )

    if action.action in CONFIRMATION_REQUIRED_ACTIONS:
        return PolicyDecision(
            allowed=True,
            reason=f"Action '{action.action}' is allowed with user confirmation.",
            requires_confirmation=True,
        )

    return PolicyDecision(
        allowed=True,
        reason=f"Action '{action.action}' is allowed by the current Phase 4 policy.",
    )


def evaluate_policy(payload: str | dict[str, object] | AgentAction) -> PolicyDecision:
    """Evaluates policy for either raw payloads or parsed actions."""
    action = payload if isinstance(payload, AgentAction) else parse_agent_action(payload)
    return evaluate_action_policy(action)


def should_require_confirmation(payload: str | dict[str, object] | AgentAction) -> bool:
    return evaluate_policy(payload).requires_confirmation


__all__ = [
    "evaluate_policy",
    "should_require_confirmation",
    "evaluate_action_policy",
    "PolicyDecision",
]
