"""Policy engine facade."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from router.schema import AgentAction, parse_agent_action


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False
    requires_strong_confirmation: bool = False


@dataclass(frozen=True)
class DynamicSafetySettings:
    enabled: bool = False
    sensitive_context_keywords: tuple[str, ...] = ()


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
DEFAULT_SENSITIVE_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "password",
    "passcode",
    "otp",
    "2fa",
    "bank",
    "payment",
    "wallet",
    "credit card",
    "ssn",
    "private key",
    "token",
    "credential",
    "invoice",
)
STRONG_CONFIRMATION_ACTIONS = {
    "pc.type_text",
    "android.capture_screenshot",
    "pc.ocr_screen",
    "pc.ocr_image",
}


def _coerce_scalar(value: str) -> object:
    normalized = value.strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"1", "0"}:
        return lowered == "1"
    try:
        if any(char in normalized for char in {".", "e", "E"}):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized.strip('"').strip("'")


def _load_settings_values() -> dict[str, object]:
    settings_path = Path(
        os.getenv("AI_LAN_SETTINGS_PATH", str(ROOT / "config" / "settings.yaml"))
    )
    if not settings_path.exists():
        return {}

    values: dict[str, object] = {}
    for raw_line in settings_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)
    return values


def _normalize_keywords(raw_value: object) -> tuple[str, ...]:
    if isinstance(raw_value, str):
        parts = [segment.strip().lower() for segment in raw_value.split(",")]
        return tuple(part for part in parts if part)
    if isinstance(raw_value, list):
        keywords: list[str] = []
        for item in raw_value:
            if isinstance(item, str) and item.strip():
                keywords.append(item.strip().lower())
        return tuple(keywords)
    return ()


def _load_dynamic_safety_settings() -> DynamicSafetySettings:
    values = _load_settings_values()
    enabled_raw = values.get("dynamic_safety_enabled", False)
    if isinstance(enabled_raw, bool):
        enabled = enabled_raw
    elif isinstance(enabled_raw, (int, float)):
        enabled = bool(enabled_raw)
    elif isinstance(enabled_raw, str):
        enabled = enabled_raw.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = False

    keywords = _normalize_keywords(values.get("sensitive_context_keywords"))
    if not keywords:
        keywords = DEFAULT_SENSITIVE_CONTEXT_KEYWORDS

    return DynamicSafetySettings(enabled=enabled, sensitive_context_keywords=keywords)


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
DYNAMIC_SAFETY_SETTINGS = _load_dynamic_safety_settings()


def _is_sensitive_context(policy_context: dict[str, Any] | None) -> bool:
    if not DYNAMIC_SAFETY_SETTINGS.enabled:
        return False
    if not policy_context:
        return False

    explicit_flag = policy_context.get("sensitive_context")
    if isinstance(explicit_flag, bool):
        return explicit_flag

    inspected_text = " ".join(
        [
            str(policy_context.get("perception_summary", "")),
            str(policy_context.get("query", "")),
            str(policy_context.get("assembled_context", "")),
        ]
    ).lower()
    return any(keyword in inspected_text for keyword in DYNAMIC_SAFETY_SETTINGS.sensitive_context_keywords)


@sentinel
def evaluate_action_policy(
    action: AgentAction,
    *,
    policy_context: dict[str, Any] | None = None,
) -> PolicyDecision:
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
        requires_strong_confirmation = _is_sensitive_context(policy_context) and (
            action.action in STRONG_CONFIRMATION_ACTIONS
        )
        confirmation_reason = f"Action '{action.action}' is allowed with user confirmation."
        if requires_strong_confirmation:
            confirmation_reason = (
                f"Action '{action.action}' is allowed only with strong confirmation in sensitive context."
            )
        return PolicyDecision(
            allowed=True,
            reason=confirmation_reason,
            requires_confirmation=True,
            requires_strong_confirmation=requires_strong_confirmation,
        )

    if _is_sensitive_context(policy_context) and action.action in STRONG_CONFIRMATION_ACTIONS:
        return PolicyDecision(
            allowed=True,
            reason=(
                f"Action '{action.action}' requires strong confirmation because sensitive context is active."
            ),
            requires_confirmation=True,
            requires_strong_confirmation=True,
        )

    return PolicyDecision(
        allowed=True,
        reason=f"Action '{action.action}' is allowed by the current Phase 4 policy.",
    )


def evaluate_policy(
    payload: str | dict[str, object] | AgentAction,
    *,
    policy_context: dict[str, Any] | None = None,
) -> PolicyDecision:
    """Evaluates policy for either raw payloads or parsed actions."""
    action = payload if isinstance(payload, AgentAction) else parse_agent_action(payload)
    return evaluate_action_policy(action, policy_context=policy_context)


def should_require_confirmation(
    payload: str | dict[str, object] | AgentAction,
    *,
    policy_context: dict[str, Any] | None = None,
) -> bool:
    return evaluate_policy(payload, policy_context=policy_context).requires_confirmation


__all__ = [
    "evaluate_policy",
    "should_require_confirmation",
    "evaluate_action_policy",
    "PolicyDecision",
]
