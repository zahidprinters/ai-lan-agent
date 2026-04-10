from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from debug_utils import sentinel

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS_PATH = ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class StorageRetentionSettings:
    temp_retention_days: int = 14
    benchmark_retention_days: int = 30
    download_retention_days: int = 45
    temp_soft_limit_mb: int = 2048


@dataclass(frozen=True)
class CleanupItem:
    path: str
    category: str
    age_days: int
    size_bytes: int


@dataclass(frozen=True)
class CleanupPlan:
    dry_run: bool
    scanned_at: str
    deleted_count: int
    deleted_bytes: int
    kept_count: int
    kept_bytes: int
    items: list[CleanupItem]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [asdict(item) for item in self.items]
        return payload


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
def load_storage_retention_settings(
    settings_path: Path | None = None,
) -> StorageRetentionSettings:
    path = settings_path or DEFAULT_SETTINGS_PATH
    if not path.exists():
        return StorageRetentionSettings()

    values: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)

    def _as_int(key: str, default: int, minimum: int, maximum: int) -> int:
        raw = values.get(key, default)
        if not isinstance(raw, (int, float)):
            return default
        bounded = int(raw)
        return max(minimum, min(bounded, maximum))

    return StorageRetentionSettings(
        temp_retention_days=_as_int("storage_temp_retention_days", 14, 1, 365),
        benchmark_retention_days=_as_int("storage_benchmark_retention_days", 30, 1, 365),
        download_retention_days=_as_int("storage_download_retention_days", 45, 1, 365),
        temp_soft_limit_mb=_as_int("storage_temp_soft_limit_mb", 2048, 128, 102400),
    )


@sentinel
def _directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


@sentinel
def build_storage_health_payload(
    *,
    project_root: Path | None = None,
    settings_path: Path | None = None,
) -> dict[str, Any]:
    root = project_root or ROOT
    settings = load_storage_retention_settings(settings_path)

    targets = {
        "temp": root / "temp",
        "runs": root / "runs",
        "models": root / "models",
        "data": root / "data",
        "logs": root / "logs",
    }

    usage = []
    for name, path in targets.items():
        size_bytes = _directory_size_bytes(path)
        usage.append(
            {
                "name": name,
                "path": str(path),
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
            }
        )

    usage.sort(key=lambda item: float(item["size_bytes"]), reverse=True)
    temp_size_bytes = next((int(item["size_bytes"]) for item in usage if item["name"] == "temp"), 0)
    temp_soft_limit_bytes = settings.temp_soft_limit_mb * 1024 * 1024

    try:
        disk = (root / "temp").resolve()
        disk_usage = disk.stat().st_dev
        _ = disk_usage
    except OSError:
        pass

    import shutil

    disk_target = (root / "temp") if (root / "temp").exists() else root
    total, used, free = shutil.disk_usage(disk_target)

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "retention": asdict(settings),
        "usage": usage,
        "temp_soft_limit": {
            "limit_mb": settings.temp_soft_limit_mb,
            "limit_bytes": temp_soft_limit_bytes,
            "current_mb": round(temp_size_bytes / (1024 * 1024), 2),
            "current_bytes": temp_size_bytes,
            "exceeded": temp_size_bytes > temp_soft_limit_bytes,
        },
        "disk": {
            "path": str(disk_target.resolve()),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_gb": round(free / (1024 * 1024 * 1024), 2),
        },
    }


def _iter_cleanup_targets(root: Path) -> list[tuple[str, Path, str]]:
    return [
        ("benchmarks", root / "temp" / "benchmarks", "benchmark"),
        ("downloads", root / "temp" / "downloads", "download"),
        ("android", root / "temp" / "android", "temp"),
        ("ingestion", root / "temp" / "ingestion", "temp"),
        ("pytest", root / "temp" / "pytest", "temp"),
        ("logs", root / "temp" / "logs", "temp"),
    ]


def _retention_days_for_category(settings: StorageRetentionSettings, category: str) -> int:
    if category == "benchmark":
        return settings.benchmark_retention_days
    if category == "download":
        return settings.download_retention_days
    return settings.temp_retention_days


@sentinel
def run_storage_cleanup(
    *,
    dry_run: bool = True,
    project_root: Path | None = None,
    settings_path: Path | None = None,
) -> CleanupPlan:
    root = project_root or ROOT
    settings = load_storage_retention_settings(settings_path)
    now = datetime.now(timezone.utc)

    deleted_count = 0
    deleted_bytes = 0
    kept_count = 0
    kept_bytes = 0
    items: list[CleanupItem] = []

    for _, target_root, category in _iter_cleanup_targets(root):
        if not target_root.exists():
            continue

        retention_days = _retention_days_for_category(settings, category)
        cutoff = now - timedelta(days=retention_days)

        for file_path in target_root.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue

            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            age_days = max((now - modified).days, 0)
            item = CleanupItem(
                path=str(file_path),
                category=category,
                age_days=age_days,
                size_bytes=int(stat.st_size),
            )

            if modified <= cutoff:
                items.append(item)
                if dry_run:
                    kept_count += 1
                    kept_bytes += item.size_bytes
                else:
                    try:
                        file_path.unlink()
                    except OSError:
                        kept_count += 1
                        kept_bytes += item.size_bytes
                    else:
                        deleted_count += 1
                        deleted_bytes += item.size_bytes

    if not dry_run:
        for _, target_root, _ in _iter_cleanup_targets(root):
            if not target_root.exists():
                continue
            for directory in sorted([p for p in target_root.rglob("*") if p.is_dir()], reverse=True):
                try:
                    if not any(directory.iterdir()):
                        directory.rmdir()
                except OSError:
                    continue

    return CleanupPlan(
        dry_run=dry_run,
        scanned_at=now.isoformat(),
        deleted_count=deleted_count,
        deleted_bytes=deleted_bytes,
        kept_count=kept_count,
        kept_bytes=kept_bytes,
        items=items,
    )


@sentinel
def write_cleanup_report(path: Path, plan: CleanupPlan) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")


__all__ = [
    "StorageRetentionSettings",
    "CleanupItem",
    "CleanupPlan",
    "build_storage_health_payload",
    "load_storage_retention_settings",
    "run_storage_cleanup",
    "write_cleanup_report",
]
