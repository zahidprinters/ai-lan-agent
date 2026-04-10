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
DEFAULT_QUALITY_DIR = ROOT / "runs" / "quality"
DEFAULT_SETTINGS_PATH = ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class ModelRecord:
    version: str
    model_path: str
    created_at: str
    metrics: dict[str, float]
    tags: list[str]
    notes: str


@dataclass(frozen=True)
class QualityGuardrailSettings:
    min_score: float = 0.0
    baseline_model: str | None = None


class RegistryPayload(TypedDict):
    active_version: str | None
    records: list[dict[str, Any]]


def _empty_registry_payload() -> RegistryPayload:
    return {"active_version": None, "records": []}


def _coerce_scalar(value: str) -> object:
    normalized = value.strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if any(char in normalized for char in {".", "e", "E"}):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized.strip('"').strip("'")


@sentinel
def load_quality_guardrail_settings(
    settings_path: Path | None = None,
) -> QualityGuardrailSettings:
    path = settings_path or DEFAULT_SETTINGS_PATH
    if not path.exists():
        return QualityGuardrailSettings()

    values: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)

    min_score_raw = values.get("quality_guardrail_min_score", 0.0)
    baseline_raw = values.get("quality_guardrail_baseline_model")
    min_score = float(min_score_raw) if isinstance(min_score_raw, (int, float)) else 0.0
    baseline = str(baseline_raw).strip() if isinstance(baseline_raw, str) else None
    return QualityGuardrailSettings(
        min_score=min_score,
        baseline_model=baseline or None,
    )


@sentinel
def find_quality_benchmark_artifact(
    *,
    model_version: str | None = None,
    model_path: str | None = None,
    quality_dir: Path | None = None,
) -> dict[str, Any] | None:
    search_dir = quality_dir or DEFAULT_QUALITY_DIR
    if not search_dir.exists():
        return None

    for artifact_path in sorted(search_dir.glob("*.json"), reverse=True):
        try:
            payload_obj: object = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload_obj, dict):
            continue
        payload = {str(key): value for key, value in payload_obj.items()}
        artifact_version = payload.get("model_version")
        artifact_model_path = payload.get("model_path")
        if model_version and artifact_version == model_version:
            payload["artifact_path"] = str(artifact_path)
            return payload
        if model_path and artifact_model_path == model_path:
            payload["artifact_path"] = str(artifact_path)
            return payload
    return None


def _coerce_score(payload: dict[str, Any], *, label: str) -> float:
    score = payload.get("score")
    if not isinstance(score, (int, float)):
        raise ValueError(f"Quality benchmark artifact for {label} is missing numeric 'score'.")
    return float(score)


@sentinel
def enforce_quality_guardrail(
    version: str,
    *,
    registry_path: Path | None = None,
    settings_path: Path | None = None,
    quality_dir: Path | None = None,
) -> dict[str, Any]:
    path = init_registry(registry_path)
    payload = _read_registry(path)
    candidate = next(
        (record for record in payload["records"] if str(record.get("version", "")) == version),
        None,
    )
    if candidate is None:
        raise ValueError(f"Unknown model version: {version}")

    settings = load_quality_guardrail_settings(settings_path)
    candidate_artifact = find_quality_benchmark_artifact(
        model_version=version,
        model_path=str(candidate.get("model_path", "")),
        quality_dir=quality_dir,
    )
    if candidate_artifact is None:
        raise FileNotFoundError(
            f"Quality benchmark artifact not found for candidate version '{version}'."
        )

    candidate_score = _coerce_score(candidate_artifact, label=f"candidate '{version}'")
    if candidate_score < settings.min_score:
        raise ValueError(
            f"Candidate quality score {candidate_score:.4f} is below the configured minimum "
            f"{settings.min_score:.4f}."
        )

    baseline_version = settings.baseline_model or payload.get("active_version")
    if baseline_version and baseline_version != version:
        baseline = next(
            (
                record
                for record in payload["records"]
                if str(record.get("version", "")) == str(baseline_version)
            ),
            None,
        )
        if baseline is None:
            raise ValueError(f"Configured baseline model version not found: {baseline_version}")
        baseline_artifact = find_quality_benchmark_artifact(
            model_version=str(baseline_version),
            model_path=str(baseline.get("model_path", "")),
            quality_dir=quality_dir,
        )
        if baseline_artifact is None:
            raise FileNotFoundError(
                f"Quality benchmark artifact not found for baseline version '{baseline_version}'."
            )
        baseline_score = _coerce_score(
            baseline_artifact, label=f"baseline '{baseline_version}'"
        )
        if candidate_score < baseline_score:
            raise ValueError(
                f"Candidate quality score {candidate_score:.4f} is below baseline "
                f"{baseline_score:.4f}."
            )

    return candidate_artifact


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
def promote_model(
    version: str,
    *,
    registry_path: Path | None = None,
    settings_path: Path | None = None,
    quality_dir: Path | None = None,
) -> RegistryPayload:
    enforce_quality_guardrail(
        version,
        registry_path=registry_path,
        settings_path=settings_path,
        quality_dir=quality_dir,
    )
    return set_active_model(version, registry_path=registry_path)


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
