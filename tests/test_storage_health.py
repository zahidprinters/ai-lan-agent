from __future__ import annotations

import json
from pathlib import Path

from tools.storage_health import build_storage_health_payload, run_storage_cleanup


def test_build_storage_health_payload_includes_usage_and_limits(tmp_path: Path) -> None:
    (tmp_path / "temp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "models").mkdir(parents=True, exist_ok=True)
    (tmp_path / "temp" / "benchmarks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "temp" / "benchmarks" / "sample.json").write_text("{}", encoding="utf-8")

    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "storage_temp_retention_days: 7\n"
        "storage_benchmark_retention_days: 14\n"
        "storage_download_retention_days: 21\n"
        "storage_temp_soft_limit_mb: 1\n",
        encoding="utf-8",
    )

    payload = build_storage_health_payload(project_root=tmp_path, settings_path=settings_path)

    assert payload["status"] == "ok"
    assert payload["retention"]["temp_retention_days"] == 7
    assert any(item["name"] == "temp" for item in payload["usage"])
    assert "temp_soft_limit" in payload


def test_run_storage_cleanup_dry_run_reports_candidates(tmp_path: Path) -> None:
    benchmarks_dir = tmp_path / "temp" / "benchmarks"
    benchmarks_dir.mkdir(parents=True, exist_ok=True)
    old_file = benchmarks_dir / "old.json"
    old_file.write_text(json.dumps({"old": True}), encoding="utf-8")

    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "storage_temp_retention_days: 1\n"
        "storage_benchmark_retention_days: 1\n"
        "storage_download_retention_days: 1\n"
        "storage_temp_soft_limit_mb: 32\n",
        encoding="utf-8",
    )

    import os
    import time

    two_days_ago = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_file, (two_days_ago, two_days_ago))

    plan = run_storage_cleanup(dry_run=True, project_root=tmp_path, settings_path=settings_path)

    assert plan.dry_run is True
    assert plan.items
    assert old_file.exists()
