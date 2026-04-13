"""Home Assistant tool facade with safe defaults."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from debug_utils import sentinel


def _home_base_url() -> str:
    return os.getenv("AI_LAN_HOME_ASSISTANT_URL", "").strip().rstrip("/")


def _home_token() -> str:
    return os.getenv("AI_LAN_HOME_ASSISTANT_TOKEN", "").strip()


def _allow_home_side_effects() -> bool:
    return os.getenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_csv_allowlist(env_key: str) -> set[str]:
    raw = os.getenv(env_key, "")
    values = [entry.strip().lower() for entry in raw.split(",")]
    return {value for value in values if value}


def _extract_entity_ids(service_data: dict[str, object]) -> list[str]:
    raw_entity_id = service_data.get("entity_id")
    if raw_entity_id is None:
        return []
    if isinstance(raw_entity_id, str):
        normalized = raw_entity_id.strip().lower()
        return [normalized] if normalized else []
    if isinstance(raw_entity_id, list):
        entity_ids: list[str] = []
        for item in raw_entity_id:
            if isinstance(item, str):
                normalized = item.strip().lower()
                if normalized:
                    entity_ids.append(normalized)
        return entity_ids
    return []


def _request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    timeout_seconds: int = 10,
) -> tuple[int, object] | tuple[None, str]:
    base_url = _home_base_url()
    token = _home_token()
    if not base_url:
        return None, "Set AI_LAN_HOME_ASSISTANT_URL to enable Home Assistant reads."
    if not token:
        return None, "Set AI_LAN_HOME_ASSISTANT_TOKEN to enable Home Assistant API access."

    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    req = request.Request(
        f"{base_url}{path}",
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=body,
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return status_code, {}
            return status_code, json.loads(raw)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, f"Home Assistant HTTP error {exc.code}: {detail or exc.reason}"
    except error.URLError as exc:
        return None, f"Home Assistant connection error: {exc.reason}"
    except Exception as exc:
        return None, f"Home Assistant request failed: {exc}"


@sentinel
def list_entities(
    domain: str | None = None,
    state: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    status_code, payload = _request_json("GET", "/api/states")
    if status_code is None:
        return {"status": "unavailable", "detail": str(payload), "count": 0, "entities": []}
    if status_code < 200 or status_code >= 300:
        return {
            "status": "failed",
            "detail": f"Unexpected Home Assistant status code {status_code}.",
            "count": 0,
            "entities": [],
        }
    if not isinstance(payload, list):
        return {
            "status": "failed",
            "detail": "Home Assistant returned a non-list payload for /api/states.",
            "count": 0,
            "entities": [],
        }

    normalized_domain = (domain or "").strip().lower()
    normalized_state = (state or "").strip().lower()
    max_limit = max(1, min(int(limit), 500))

    entities: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        entity_id = str(item.get("entity_id", "")).strip()
        entity_state = str(item.get("state", "")).strip()
        if not entity_id:
            continue
        if normalized_domain and not entity_id.lower().startswith(f"{normalized_domain}."):
            continue
        if normalized_state and entity_state.lower() != normalized_state:
            continue

        attributes = item.get("attributes", {})
        friendly_name = ""
        if isinstance(attributes, dict):
            friendly_name = str(attributes.get("friendly_name", "")).strip()

        entities.append(
            {
                "entity_id": entity_id,
                "state": entity_state,
                "friendly_name": friendly_name,
                "last_changed": str(item.get("last_changed", "")),
            }
        )
        if len(entities) >= max_limit:
            break

    return {
        "status": "ok",
        "detail": "",
        "count": len(entities),
        "entities": entities,
    }


@sentinel
def call_service(
    domain: str,
    service: str,
    service_data: dict[str, object] | None = None,
) -> dict[str, object]:
    if not _allow_home_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_HOME_ALLOW_SIDE_EFFECTS=1 to enable Home Assistant service calls.",
        }

    normalized_domain = domain.strip().lower()
    normalized_service = service.strip().lower()
    if not normalized_domain or not normalized_service:
        return {"status": "failed", "detail": "Both domain and service are required."}

    allowed_services = _parse_csv_allowlist("AI_LAN_HOME_ALLOWED_SERVICES")
    if not allowed_services:
        return {
            "status": "blocked_policy",
            "detail": "Set AI_LAN_HOME_ALLOWED_SERVICES to allow Home Assistant service calls.",
        }

    service_key = f"{normalized_domain}.{normalized_service}"
    if service_key not in allowed_services:
        return {
            "status": "blocked_policy",
            "detail": "Service is not in AI_LAN_HOME_ALLOWED_SERVICES allowlist.",
        }

    normalized_service_data = service_data or {}
    entity_ids = _extract_entity_ids(normalized_service_data)
    if entity_ids:
        allowed_entities = _parse_csv_allowlist("AI_LAN_HOME_ALLOWED_ENTITIES")
        if not allowed_entities:
            return {
                "status": "blocked_policy",
                "detail": "Set AI_LAN_HOME_ALLOWED_ENTITIES when service_data includes entity_id.",
            }
        for entity_id in entity_ids:
            if entity_id not in allowed_entities:
                return {
                    "status": "blocked_policy",
                    "detail": "Entity is not in AI_LAN_HOME_ALLOWED_ENTITIES allowlist.",
                }

    status_code, payload = _request_json(
        "POST",
        f"/api/services/{normalized_domain}/{normalized_service}",
        payload=normalized_service_data,
    )
    if status_code is None:
        return {"status": "failed", "detail": str(payload)}
    if status_code < 200 or status_code >= 300:
        return {
            "status": "failed",
            "detail": f"Unexpected Home Assistant status code {status_code}.",
        }

    return {
        "status": "ok",
        "detail": "Service call accepted by Home Assistant.",
        "result": payload,
    }


__all__ = ["list_entities", "call_service"]
