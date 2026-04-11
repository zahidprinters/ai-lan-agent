from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agents.react.tool_risk import ToolRiskProfile, get_tool_risk_profile


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


@dataclass(frozen=True)
class PlanRequirements:
    task_complexity: str
    min_steps: int
    max_steps: int
    quality_checks: list[str]


@dataclass(frozen=True)
class PlanValidationResult:
    steps: list[str]
    valid: bool
    source: str
    reasons: list[str]
    risk_profile: ToolRiskProfile | None = None


def _infer_focus(message: str) -> str:
    lowered = message.strip().lower()
    if "search" in lowered or "find" in lowered:
        return "search for the needed information"
    if "context" in lowered or "memory" in lowered:
        return "gather the most relevant stored context"
    if "status" in lowered or "system" in lowered:
        return "inspect the requested system state"
    return "analyze the request and collect the minimum needed evidence"


def build_plan_requirements(
    *,
    message: str,
    task_complexity: str,
    runtime_context: dict[str, Any] | None = None,
) -> PlanRequirements:
    min_steps = _env_int("AI_LAN_REASONING_PLAN_STEPS_MIN", 3, minimum=3, maximum=5)
    max_steps = _env_int("AI_LAN_REASONING_PLAN_STEPS_MAX", 5, minimum=min_steps, maximum=5)

    context_hint = "check the available runtime context" if runtime_context else "identify whether more context is needed"
    focus = _infer_focus(message)
    quality_checks = [
        f"Return between {min_steps} and {max_steps} concise plan steps.",
        f"Include a step to understand the user goal and {context_hint}.",
        f"Include a step to {focus}.",
        "Include a step that selects the safest next tool or a direct reply using the router schema.",
        "Include a verification or reflection step before any retry.",
        "End with a grounded final reply or a safe refusal when policy blocks the action.",
    ]
    return PlanRequirements(
        task_complexity=task_complexity,
        min_steps=min_steps,
        max_steps=max_steps,
        quality_checks=quality_checks,
    )


def _normalize_candidate_steps(candidate_steps: list[str] | None) -> list[str]:
    return [step.strip() for step in (candidate_steps or []) if step.strip()]


def _build_shaped_steps(
    *,
    message: str,
    task_complexity: str,
    risk_profile: ToolRiskProfile | None,
    runtime_context: dict[str, Any] | None,
    min_steps: int,
    max_steps: int,
) -> list[str]:
    context_hint = "inspect the available runtime context" if runtime_context else "decide whether more context is required"
    focus = _infer_focus(message)
    risk_steps = ["Check policy and safety constraints for the next action."]
    if risk_profile is not None:
        if risk_profile.policy_mode == "deny":
            risk_steps = ["Check policy and prepare a safe refusal because the requested action is blocked."]
        elif risk_profile.risk_tier == "dangerous":
            risk_steps = ["Check strong confirmation and safety requirements before continuing."]
        elif risk_profile.risk_tier == "medium":
            risk_steps = ["Check confirmation requirements before continuing."]

    base_steps = [
        f"Understand the user goal and {context_hint}.",
        f"{focus.capitalize()}.",
        risk_steps[0],
        "Choose the safest next tool or direct reply using the router schema.",
        "Verify the outcome and reflect before any retry, or refuse safely if policy blocks the action.",
    ]
    desired = max_steps if task_complexity == "complex" else min_steps
    return base_steps[:desired]


def validate_or_repair_plan(
    *,
    candidate_steps: list[str] | None,
    message: str,
    task_complexity: str,
    runtime_context: dict[str, Any] | None = None,
    action_payload: dict[str, object] | None = None,
    requirements: PlanRequirements | None = None,
) -> PlanValidationResult:
    resolved_requirements = requirements or build_plan_requirements(
        message=message,
        task_complexity=task_complexity,
        runtime_context=runtime_context,
    )
    normalized = _normalize_candidate_steps(candidate_steps)
    risk_profile = None
    if action_payload and isinstance(action_payload.get("action"), str):
        risk_profile = get_tool_risk_profile(str(action_payload.get("action", "")))

    reasons: list[str] = []
    valid = True
    if not (resolved_requirements.min_steps <= len(normalized) <= resolved_requirements.max_steps):
        valid = False
        reasons.append("plan_step_count_out_of_bounds")
    if len(set(step.lower() for step in normalized)) != len(normalized):
        valid = False
        reasons.append("plan_steps_duplicate")

    combined = " ".join(step.lower() for step in normalized)
    if not any(token in combined for token in ("safe", "policy", "confirm", "refus", "verif", "reflect")):
        valid = False
        reasons.append("plan_missing_safety_or_verification")
    if risk_profile is not None and risk_profile.policy_mode == "deny":
        if not any(token in combined for token in ("refus", "deny", "block", "policy")):
            valid = False
            reasons.append("plan_missing_refusal_path")
    elif risk_profile is not None and risk_profile.risk_tier in {"medium", "dangerous"}:
        if not any(token in combined for token in ("confirm", "policy", "safe")):
            valid = False
            reasons.append("plan_missing_confirmation_path")

    if valid:
        return PlanValidationResult(
            steps=normalized,
            valid=True,
            source="model_validated",
            reasons=["plan_quality_passed"],
            risk_profile=risk_profile,
        )

    repaired = _build_shaped_steps(
        message=message,
        task_complexity=task_complexity,
        risk_profile=risk_profile,
        runtime_context=runtime_context,
        min_steps=resolved_requirements.min_steps,
        max_steps=resolved_requirements.max_steps,
    )
    return PlanValidationResult(
        steps=repaired,
        valid=False,
        source="repaired",
        reasons=reasons,
        risk_profile=risk_profile,
    )


__all__ = [
    "PlanRequirements",
    "PlanValidationResult",
    "build_plan_requirements",
    "validate_or_repair_plan",
]