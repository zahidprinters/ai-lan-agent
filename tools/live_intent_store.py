from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.memory_store import tokenize_text


def get_live_intent_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    configured = os.getenv("AI_LAN_LIVE_INTENT_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("temp") / "learning" / "live_intents.json"


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def load_live_intents(path: Path | None = None) -> list[dict[str, Any]]:
    target = get_live_intent_path(path)
    if not target.exists():
        return []
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(loaded, list):
        return []
    intents: list[dict[str, Any]] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        trigger_obj = item.get("trigger")
        payload_obj = item.get("payload")
        if not isinstance(trigger_obj, str) or not isinstance(payload_obj, dict):
            continue
        trigger = _normalize_text(trigger_obj)
        if not trigger:
            continue
        intents.append(
            {
                "trigger": trigger,
                "payload": payload_obj,
                "learned_at": str(item.get("learned_at", "")),
                "usage_count": int(item.get("usage_count", 0) or 0),
            }
        )
    return intents


def _save_live_intents(intents: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = get_live_intent_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(intents, ensure_ascii=True, indent=2), encoding="utf-8")
    return target


def learn_live_intent(
    *,
    trigger: str,
    payload: dict[str, object],
    path: Path | None = None,
) -> Path:
    normalized_trigger = _normalize_text(trigger)
    if not normalized_trigger:
        raise ValueError("Trigger cannot be empty.")

    intents = load_live_intents(path)
    replaced = False
    for item in intents:
        if item.get("trigger") == normalized_trigger:
            item["payload"] = payload
            replaced = True
            break

    if not replaced:
        intents.append(
            {
                "trigger": normalized_trigger,
                "payload": payload,
                "learned_at": "runtime",
                "usage_count": 0,
            }
        )

    return _save_live_intents(intents, path)


def _token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(tokenize_text(left))
    right_tokens = set(tokenize_text(right))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union == 0:
        return 0.0
    return overlap / union


def resolve_live_intent(
    *,
    message: str,
    path: Path | None = None,
    min_similarity: float = 0.72,
) -> dict[str, object] | None:
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return None

    intents = load_live_intents(path)
    if not intents:
        return None

    # Exact match first.
    for item in intents:
        if item.get("trigger") == normalized_message:
            payload_obj = item.get("payload")
            if isinstance(payload_obj, dict):
                return dict(payload_obj)

    best_score = 0.0
    best_payload: dict[str, object] | None = None
    for item in intents:
        trigger_obj = item.get("trigger")
        payload_obj = item.get("payload")
        if not isinstance(trigger_obj, str) or not isinstance(payload_obj, dict):
            continue
        score = _token_overlap_score(normalized_message, trigger_obj)
        if score > best_score:
            best_score = score
            best_payload = dict(payload_obj)

    if best_payload is not None and best_score >= min_similarity:
        return best_payload
    return None


__all__ = [
    "get_live_intent_path",
    "learn_live_intent",
    "load_live_intents",
    "resolve_live_intent",
]
