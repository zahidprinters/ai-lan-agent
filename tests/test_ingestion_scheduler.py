from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_settings(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "ingestion_profile_default: daily",
                "ingestion_drift_kept_drop_warn: 1",
                "ingestion_drift_avg_final_score_drop_warn: 0.05",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_ingestion_scheduler_first_run_creates_history_and_no_baseline(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    settings_path = tmp_path / "settings.yaml"
    output_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    history_path = tmp_path / "history.jsonl"
    drift_path = tmp_path / "drift.json"
    _write_settings(settings_path)

    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "good",
                    "source_type": "inline",
                    "location": (
                        "First informative line for ingestion.\n"
                        "Second informative line for ingestion.\n"
                        "Third informative line for ingestion."
                    ),
                    "trust_score": 0.9,
                    "last_updated": "2026-04-12T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingestion_scheduler.py",
            "--config",
            str(config_path),
            "--settings",
            str(settings_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--history",
            str(history_path),
            "--drift-report",
            str(drift_path),
            "--as-of",
            "2026-04-13T00:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    assert "Drift status: no_baseline" in result.stdout
    drift_payload = json.loads(drift_path.read_text(encoding="utf-8"))
    assert drift_payload["status"] == "no_baseline"
    history_lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(history_lines) == 1


def test_ingestion_scheduler_warns_on_kept_count_drop(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    settings_path = tmp_path / "settings.yaml"
    output_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    history_path = tmp_path / "history.jsonl"
    drift_path = tmp_path / "drift.json"
    _write_settings(settings_path)

    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "good",
                    "source_type": "inline",
                    "location": (
                        "First informative line for ingestion.\n"
                        "Second informative line for ingestion.\n"
                        "Third informative line for ingestion."
                    ),
                    "trust_score": 0.9,
                    "last_updated": "2026-04-12T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/ingestion_scheduler.py",
            "--config",
            str(config_path),
            "--settings",
            str(settings_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--history",
            str(history_path),
            "--drift-report",
            str(drift_path),
            "--as-of",
            "2026-04-13T00:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingestion_scheduler.py",
            "--config",
            str(config_path),
            "--settings",
            str(settings_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--history",
            str(history_path),
            "--drift-report",
            str(drift_path),
            "--as-of",
            "2026-04-13T00:00:00Z",
            "--min-final-score",
            "0.98",
            "--drift-kept-drop-warn",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    assert "Drift status: warn" in result.stdout
    drift_payload = json.loads(drift_path.read_text(encoding="utf-8"))
    assert drift_payload["status"] == "warn"
    assert "kept_count_drop" in drift_payload["warnings"]
