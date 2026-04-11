from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from agents.react.tool_risk import ToolRiskProfile, get_tool_risk_profile
from router.schema import ActionSchemaError, parse_agent_action


@dataclass(frozen=True)
class RuntimeDispatchDecision:
    allowed: bool
    reason: str
    risk_profile: ToolRiskProfile

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["risk_profile"] = self.risk_profile.to_dict()
        return payload


@dataclass(frozen=True)
class ExecutionContractVerification:
    valid: bool
    reason: str
    payload_signature: str
    stream_payload_signature: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _canonicalize_action_payload(action_payload: dict[str, object]) -> dict[str, object]:
    try:
        return parse_agent_action(action_payload).to_dict()
    except ActionSchemaError:
        filtered = {
            key: action_payload[key]
            for key in ("thought", "action", "args", "safety_level")
            if key in action_payload
        }
        return {str(key): value for key, value in filtered.items()}


def _payload_signature(action_payload: dict[str, object]) -> str:
    canonical_payload = _canonicalize_action_payload(action_payload)
    encoded = json.dumps(canonical_payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _metadata_to_dict(metadata: object) -> dict[str, object]:
    return dict(metadata) if isinstance(metadata, dict) else {}


def build_execution_contract(
    *,
    action_payload: dict[str, object],
    metadata: dict[str, object] | None,
    runtime_guard: RuntimeDispatchDecision,
) -> dict[str, object]:
    runtime_metadata = _metadata_to_dict(metadata)
    stream_payload_signature: str | None = None
    stream_payload = runtime_metadata.get("stream_trigger_payload")
    if isinstance(stream_payload, dict):
        stream_payload_signature = _payload_signature(stream_payload)

    return {
        "payload_signature": _payload_signature(action_payload),
        "guard_allowed": runtime_guard.allowed,
        "guard_reason": runtime_guard.reason,
        "stream_payload_signature": stream_payload_signature,
    }


def verify_execution_contract(
    *,
    action_payload: dict[str, object],
    metadata: dict[str, object] | None,
) -> ExecutionContractVerification:
    runtime_metadata = _metadata_to_dict(metadata)
    contract_obj = runtime_metadata.get("execution_contract")
    payload_signature = _payload_signature(action_payload)
    stream_payload_signature: str | None = None

    if not isinstance(contract_obj, dict):
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_missing",
            payload_signature=payload_signature,
        )

    contract_payload_signature = str(contract_obj.get("payload_signature", "")).strip()
    if not contract_payload_signature:
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_signature_missing",
            payload_signature=payload_signature,
        )

    if payload_signature != contract_payload_signature:
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_payload_mismatch",
            payload_signature=payload_signature,
        )

    runtime_guard_obj = runtime_metadata.get("runtime_guard")
    if not isinstance(runtime_guard_obj, dict):
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_runtime_guard_missing",
            payload_signature=payload_signature,
        )

    guard_allowed = bool(runtime_guard_obj.get("allowed", False))
    guard_reason = str(runtime_guard_obj.get("reason", "")).strip()
    if guard_allowed != bool(contract_obj.get("guard_allowed", False)):
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_guard_drift",
            payload_signature=payload_signature,
        )
    if guard_reason != str(contract_obj.get("guard_reason", "")).strip():
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_guard_reason_drift",
            payload_signature=payload_signature,
        )
    if not guard_allowed:
        return ExecutionContractVerification(
            valid=False,
            reason="execution_contract_guard_denied",
            payload_signature=payload_signature,
        )

    stream_payload = runtime_metadata.get("stream_trigger_payload")
    if isinstance(stream_payload, dict):
        stream_payload_signature = _payload_signature(stream_payload)
        if stream_payload_signature != str(contract_obj.get("stream_payload_signature", "")).strip():
            return ExecutionContractVerification(
                valid=False,
                reason="execution_contract_stream_signature_drift",
                payload_signature=payload_signature,
                stream_payload_signature=stream_payload_signature,
            )
        if stream_payload_signature != payload_signature:
            return ExecutionContractVerification(
                valid=False,
                reason="execution_contract_stream_payload_mismatch",
                payload_signature=payload_signature,
                stream_payload_signature=stream_payload_signature,
            )

    return ExecutionContractVerification(
        valid=True,
        reason="execution_contract_verified",
        payload_signature=payload_signature,
        stream_payload_signature=stream_payload_signature,
    )


def _plan_steps_from_metadata(metadata: dict[str, object]) -> list[str]:
    raw_steps = metadata.get("plan_steps")
    if not isinstance(raw_steps, list):
        return []
    return [str(step).strip() for step in raw_steps if str(step).strip()]


def _plan_validation_source(metadata: dict[str, object]) -> str:
    raw_validation = metadata.get("plan_validation")
    if not isinstance(raw_validation, dict):
        return ""
    return str(raw_validation.get("source", "")).strip().lower()


def _action_tokens(action_name: str) -> list[str]:
    normalized = action_name.strip().lower()
    parts = normalized.replace(".", "_").split("_")
    return [token for token in parts if len(token) >= 3]


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def evaluate_runtime_dispatch_guard(
    *,
    action_payload: dict[str, object],
    metadata: dict[str, object] | None = None,
) -> RuntimeDispatchDecision:
    action_name = str(action_payload.get("action", "")).strip().lower()
    risk_profile = get_tool_risk_profile(action_name)
    runtime_metadata = _metadata_to_dict(metadata)
    trigger_mode = str(runtime_metadata.get("stream_trigger_mode", "")).strip().lower()
    plan_steps = _plan_steps_from_metadata(runtime_metadata)
    plan_text = " ".join(plan_steps).lower()

    if risk_profile.policy_mode == "deny":
        return RuntimeDispatchDecision(
            allowed=False,
            reason="runtime_risk_policy_deny",
            risk_profile=risk_profile,
        )

    if trigger_mode in {"json_action", "text_action"}:
        source = _plan_validation_source(runtime_metadata)
        if source not in {"model_validated", "repaired"}:
            return RuntimeDispatchDecision(
                allowed=False,
                reason="runtime_plan_validation_missing",
                risk_profile=risk_profile,
            )
        if not plan_steps:
            return RuntimeDispatchDecision(
                allowed=False,
                reason="runtime_plan_steps_missing",
                risk_profile=risk_profile,
            )

        token_match = _contains_any(plan_text, tuple(_action_tokens(action_name)))
        tool_intent = _contains_any(plan_text, ("tool", "action", "dispatch", "execute"))
        if not token_match and not tool_intent:
            return RuntimeDispatchDecision(
                allowed=False,
                reason="runtime_stream_trigger_plan_mismatch",
                risk_profile=risk_profile,
            )

    if risk_profile.risk_tier in {"medium", "dangerous"}:
        if plan_steps and not _contains_any(plan_text, ("confirm", "policy", "safe")):
            return RuntimeDispatchDecision(
                allowed=False,
                reason="runtime_risk_confirmation_path_missing",
                risk_profile=risk_profile,
            )

    return RuntimeDispatchDecision(
        allowed=True,
        reason="runtime_guard_pass",
        risk_profile=risk_profile,
    )


__all__ = [
    "ExecutionContractVerification",
    "RuntimeDispatchDecision",
    "build_execution_contract",
    "evaluate_runtime_dispatch_guard",
    "verify_execution_contract",
]