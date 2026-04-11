from __future__ import annotations

from dataclasses import asdict, dataclass

from safety.policy_engine import (
    ALLOWED_ACTIONS,
    CONFIRMATION_REQUIRED_ACTIONS,
    DENIED_ACTIONS,
    STRONG_CONFIRMATION_ACTIONS,
)


@dataclass(frozen=True)
class ToolRiskProfile:
    action: str
    risk_tier: str
    policy_mode: str
    confirmation_required: bool
    requires_strong_confirmation: bool
    risk_reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def get_tool_risk_profile(action_name: str) -> ToolRiskProfile:
    normalized = action_name.strip().lower()
    reasons: list[str] = []
    policy_mode = "allow"
    confirmation_required = normalized in CONFIRMATION_REQUIRED_ACTIONS
    requires_strong_confirmation = normalized in STRONG_CONFIRMATION_ACTIONS

    if normalized in DENIED_ACTIONS:
        policy_mode = "deny"
        reasons.append("action denied by policy")
        risk_tier = "dangerous"
    elif requires_strong_confirmation:
        policy_mode = "confirm"
        reasons.append("strong confirmation required")
        risk_tier = "dangerous"
    elif confirmation_required:
        policy_mode = "confirm"
        reasons.append("confirmation required")
        risk_tier = "medium"
    elif normalized in ALLOWED_ACTIONS:
        reasons.append("allowed read or low-risk action")
        risk_tier = "safe"
    else:
        reasons.append("unregistered or unknown policy state")
        risk_tier = "dangerous"
        policy_mode = "deny"

    return ToolRiskProfile(
        action=normalized,
        risk_tier=risk_tier,
        policy_mode=policy_mode,
        confirmation_required=confirmation_required,
        requires_strong_confirmation=requires_strong_confirmation,
        risk_reasons=reasons,
    )


__all__ = ["ToolRiskProfile", "get_tool_risk_profile"]