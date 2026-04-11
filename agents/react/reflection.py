from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agents.react.controller import build_reflection_payload, is_reflection_candidate


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ReflectionDecision:
    retry_allowed: bool
    reason: str
    note: str
    next_payload: dict[str, object] | None = None


def evaluate_reflection_policy(
    *,
    action_payload: dict[str, object],
    result: dict[str, Any],
    retry_index: int,
    retries_for_step: int,
    retries_for_turn: int,
    max_reflection_retries_per_step: int,
    max_reflection_retries_per_turn: int,
    confirmed: bool,
) -> ReflectionDecision:
    if confirmed:
        return ReflectionDecision(False, "confirmed_action", "Reflection skipped after confirmation.")
    if retries_for_step >= max_reflection_retries_per_step:
        return ReflectionDecision(False, "step_budget_exhausted", "Reflection budget for this step is exhausted.")
    if retries_for_turn >= max_reflection_retries_per_turn:
        return ReflectionDecision(False, "retry_budget_exhausted", "Reflection budget for this turn is exhausted.")

    status = str(result.get("status", "unknown")).strip().lower()
    required_on_failure = _env_bool("AI_LAN_REFLECTION_REQUIRED_ON_FAILURE", True)
    if required_on_failure and status in {"executed", "confirmation_required", "rejected"}:
        if not is_reflection_candidate(action_payload, result):
            return ReflectionDecision(False, "no_recovery_candidate", "No reflection was needed for the result.")

    if not is_reflection_candidate(action_payload, result):
        return ReflectionDecision(False, "no_recovery_candidate", "No deterministic recovery path was identified.")

    reflected_payload = build_reflection_payload(action_payload, result, retry_index=retry_index)
    if reflected_payload is None:
        return ReflectionDecision(False, "no_recovery_candidate", "Reflection could not produce a safe retry payload.")

    note = f"Reflection retry prepared after status={status or 'unknown'} with safer adjusted arguments."
    return ReflectionDecision(True, "retry", note, reflected_payload)


__all__ = ["ReflectionDecision", "evaluate_reflection_policy"]