from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()

from debug_utils import sentinel

DEFAULT_REGISTRY_PATH = ROOT / "runs" / "model_registry.json"


@dataclass(frozen=True)
class ModelRecord:
    version: str
    model_path: str
    created_at: str
    metrics: dict[str, float]
    tags: list[str]
    notes: str


class RegistryPayload(TypedDict):
    active_version: str | None
    records: list[dict[str, Any]]


def _empty_registry_payload() -> RegistryPayload:
    return {"active_version": None, "records": []}


@sentinel
def _read_registry(path: Path) -> RegistryPayload:
    if not path.exists():
        return _empty_registry_payload()

    raw_obj: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_obj, dict):
        return _empty_registry_payload()

    active_raw: object = raw_obj.get("active_version")
    active_version = active_raw if isinstance(active_raw, str) else None

    records: list[dict[str, Any]] = []
    records_raw: object = raw_obj.get("records", [])
    if isinstance(records_raw, list):
        for item in records_raw:
            if isinstance(item, dict):
                records.append({str(key): value for key, value in item.items()})

    return {"active_version": active_version, "records": records}


@sentinel
def _write_registry(path: Path, payload: RegistryPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


@sentinel
def init_registry(registry_path: Path | None = None) -> Path:
    path = registry_path or DEFAULT_REGISTRY_PATH
    if not path.exists():
        _write_registry(path, _empty_registry_payload())
    return path


@sentinel
def register_model(
    model_path: Path,
    *,
    metrics: dict[str, float] | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    registry_path: Path | None = None,
) -> ModelRecord:
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    path = init_registry(registry_path)
    payload = _read_registry(path)
    created_at = datetime.now(timezone.utc).isoformat()
    version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    record = ModelRecord(
        version=version,
        model_path=str(model_path),
        created_at=created_at,
        metrics=metrics or {},
        tags=tags or [],
        notes=notes,
    )
    payload["records"].append(asdict(record))
    if not payload.get("active_version"):
        payload["active_version"] = version
    _write_registry(path, payload)
    return record


@sentinel
def list_registered_models(registry_path: Path | None = None) -> list[dict[str, Any]]:
    payload = _read_registry(init_registry(registry_path))
    return list(payload["records"])


@sentinel
def set_active_model(version: str, registry_path: Path | None = None) -> RegistryPayload:
    path = init_registry(registry_path)
    payload = _read_registry(path)
    versions = {
        str(record["version"])
        for record in payload["records"]
        if isinstance(record.get("version"), str)
    }
    if version not in versions:
        raise ValueError(f"Unknown model version: {version}")
    payload["active_version"] = version
    _write_registry(path, payload)
    return payload


@sentinel
def get_active_model(registry_path: Path | None = None) -> dict[str, Any] | None:
    payload = _read_registry(init_registry(registry_path))
    active = payload["active_version"]
    if not active:
        return None
    for record in payload["records"]:
        if record.get("version") == active:
            return record
    return None


@sentinel
def rollback_to_version(version: str, registry_path: Path | None = None) -> RegistryPayload:
    return set_active_model(version, registry_path=registry_path)
