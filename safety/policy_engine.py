"""Policy engine facade."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from debug_utils import sentinel

from router.schema import AgentAction, parse_agent_action


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIRMATION_REQUIRED_ACTIONS = {
    "pc.type_text",
    "pc.open_app",
    "android.launch_app",
    "android.tap",
    "android.swipe",
    "android.capture_screenshot",
    "android.scrcpy_mirror",
    "web.browser_fetch",
}
DEFAULT_DENIED_ACTIONS = {"pc.execute_shell", "pc.move_mouse"}
DEFAULT_ALLOWED_ACTIONS = {
    "web.search",
    "web.browser_fetch",
    "memory.search",
    "context.build",
    "pc.get_system_status",
    "pc.list_running_apps",
    "pc.list_workspace_files",
    "pc.read_clipboard",
    "pc.inspect_screen",
    "pc.ocr_image",
    "pc.ocr_screen",
    "pc.type_text",
    "pc.open_app",
    "android.list_devices",
    "android.launch_app",
    "android.tap",
    "android.swipe",
    "android.capture_screenshot",
    "android.scrcpy_mirror",
}


def _parse_policy_yaml_lists(raw_text: str) -> dict[str, list[str]]:
    """Parse known list keys from a small YAML subset.

    This parser intentionally supports only the project policy format so we
    avoid adding a runtime dependency for YAML parsing in the safety path.
    """
    parsed: dict[str, list[str]] = {
        "require_confirmation": [],
        "allow_actions": [],
        "deny_actions": [],
    }
    active_list: str | None = None

    for raw_line in raw_text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped.endswith(":"):
            key = stripped[:-1].strip()
            if key in parsed:
                active_list = key
            else:
                active_list = None
            continue

        if stripped.startswith("- ") and active_list:
            value = stripped[2:].strip()
            if value:
                parsed[active_list].append(value)

    return parsed


def _load_policy_sets() -> tuple[set[str], set[str], set[str]]:
    """Load policy action sets from config/policies.yaml with safe defaults."""
    policy_path = Path(os.getenv("AI_LAN_POLICY_CONFIG_PATH", str(ROOT / "config" / "policies.yaml")))
    if not policy_path.exists():
        return (
            set(DEFAULT_ALLOWED_ACTIONS),
            set(DEFAULT_DENIED_ACTIONS),
            set(DEFAULT_CONFIRMATION_REQUIRED_ACTIONS),
        )

    try:
        content = policy_path.read_text(encoding="utf-8")
        parsed = _parse_policy_yaml_lists(content)
    except Exception:
        return (
            set(DEFAULT_ALLOWED_ACTIONS),
            set(DEFAULT_DENIED_ACTIONS),
            set(DEFAULT_CONFIRMATION_REQUIRED_ACTIONS),
        )

    allowed = set(parsed["allow_actions"]) or set(DEFAULT_ALLOWED_ACTIONS)
    denied = set(parsed["deny_actions"]) or set(DEFAULT_DENIED_ACTIONS)
    confirmation_required = (
        set(parsed["require_confirmation"]) or set(DEFAULT_CONFIRMATION_REQUIRED_ACTIONS)
    )
    return allowed, denied, confirmation_required


ALLOWED_ACTIONS, DENIED_ACTIONS, CONFIRMATION_REQUIRED_ACTIONS = _load_policy_sets()


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
