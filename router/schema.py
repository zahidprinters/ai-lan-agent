from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from debug_utils import sentinel

ALLOWED_ACTION_FIELDS = {"thought", "action", "args", "safety_level"}
ALLOWED_SAFETY_LEVELS = {"low", "medium", "high"}


class ActionSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class AgentAction:
    thought: str
    action: str
    args: dict[str, object]
    safety_level: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@sentinel
def parse_agent_action(payload: str | dict[str, object]) -> AgentAction:
    if isinstance(payload, str):
        try:
            raw_payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ActionSchemaError(f"Invalid action JSON: {exc.msg}.") from exc
    elif isinstance(payload, dict):
        raw_payload = payload
    else:
        raise ActionSchemaError("Action payload must be a JSON string or dict.")

    unknown_fields = set(raw_payload) - ALLOWED_ACTION_FIELDS
    if unknown_fields:
        fields = ", ".join(sorted(unknown_fields))
        raise ActionSchemaError(f"Unknown action fields: {fields}.")

    missing_fields = ALLOWED_ACTION_FIELDS - set(raw_payload)
    if missing_fields:
        fields = ", ".join(sorted(missing_fields))
        raise ActionSchemaError(f"Missing action fields: {fields}.")

    thought = raw_payload["thought"]
    action = raw_payload["action"]
    args = raw_payload["args"]
    safety_level = raw_payload["safety_level"]

    if not isinstance(thought, str) or not thought.strip():
        raise ActionSchemaError("Field 'thought' must be a non-empty string.")
    if not isinstance(action, str) or not action.strip():
        raise ActionSchemaError("Field 'action' must be a non-empty string.")
    if not isinstance(args, dict):
        raise ActionSchemaError("Field 'args' must be an object.")
    if not isinstance(safety_level, str):
        raise ActionSchemaError("Field 'safety_level' must be a string.")

    normalized_safety = safety_level.strip().lower()
    if normalized_safety not in ALLOWED_SAFETY_LEVELS:
        allowed = ", ".join(sorted(ALLOWED_SAFETY_LEVELS))
        raise ActionSchemaError(f"Field 'safety_level' must be one of: {allowed}.")

    return AgentAction(
        thought=thought.strip(),
        action=action.strip().lower(),
        args=args,
        safety_level=normalized_safety,
    )


__all__ = ["AgentAction", "ActionSchemaError", "parse_agent_action"]
