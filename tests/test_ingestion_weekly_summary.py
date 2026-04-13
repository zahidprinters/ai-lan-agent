from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history_entry(
    *,
    timestamp: datetime,
    profile_name: str = "daily",
    kept_count: int = 3,
    fetched_count: int = 3,
    drift_status: str = "ok",
    source_scores: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "report_path": "temp/ingestion/report.json",
        "profile_name": profile_name,
        "metrics": {
            "source_count": 1,
            "fetched_count": fetched_count,
            "kept_count": kept_count,
            "filtered_low_score_count": 0,
            "duplicate_count": 0,
            "average_final_score": 0.8,
        },
        "drift_status": drift_status,
        "source_scores": source_scores if source_scores is not None else {},
    }


# ---------------------------------------------------------------------------
# Unit tests for build_weekly_summary
# ---------------------------------------------------------------------------

def test_weekly_summary_empty_history_produces_zero_runs() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    summary = build_weekly_summary([], window_days=7, unreliable_threshold=0.4)

    assert summary["total_runs"] == 0
    assert summary["source_reliability"] == {}
    assert summary["unreliable_sources"] == []
    assert summary["avg_kept_per_run"] == 0.0
    assert summary["avg_fetched_per_run"] == 0.0
    assert summary["window_days"] == 7
    assert "generated_at" in summary


def test_weekly_summary_counts_runs_and_profiles() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    now = datetime.now(tz=UTC)
    entries = [
        _make_history_entry(timestamp=now - timedelta(days=1), profile_name="daily"),
        _make_history_entry(timestamp=now - timedelta(days=2), profile_name="deep"),
        _make_history_entry(timestamp=now - timedelta(days=3), profile_name="daily"),
    ]
    summary = build_weekly_summary(entries, window_days=7, unreliable_threshold=0.4)

    assert summary["total_runs"] == 3
    assert summary["profile_run_counts"]["daily"] == 2
    assert summary["profile_run_counts"]["deep"] == 1


def test_weekly_summary_excludes_entries_outside_window() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    now = datetime.now(tz=UTC)
    entries = [
        _make_history_entry(timestamp=now - timedelta(days=3), profile_name="daily"),
        _make_history_entry(timestamp=now - timedelta(days=10), profile_name="daily"),  # outside 7d
    ]
    summary = build_weekly_summary(entries, window_days=7, unreliable_threshold=0.4)

    assert summary["total_runs"] == 1


def test_weekly_summary_per_source_trend_improving() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    now = datetime.now(tz=UTC)
    entries = [
        _make_history_entry(
            timestamp=now - timedelta(days=5),
            source_scores={"wiki": 0.50},
        ),
        _make_history_entry(
            timestamp=now - timedelta(days=4),
            source_scores={"wiki": 0.60},
        ),
        _make_history_entry(
            timestamp=now - timedelta(days=3),
            source_scores={"wiki": 0.75},
        ),
        _make_history_entry(
            timestamp=now - timedelta(days=2),
            source_scores={"wiki": 0.85},
        ),
    ]
    summary = build_weekly_summary(entries, window_days=7, unreliable_threshold=0.4)

    wiki = summary["source_reliability"]["wiki"]
    assert wiki["trend"] == "improving"
    assert wiki["run_count"] == 4
    assert wiki["avg_final_score"] > 0.6


def test_weekly_summary_flags_unreliable_source() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    now = datetime.now(tz=UTC)
    entries = [
        _make_history_entry(
            timestamp=now - timedelta(days=2),
            source_scores={"bad_source": 0.20, "good_source": 0.85},
        ),
        _make_history_entry(
            timestamp=now - timedelta(days=1),
            source_scores={"bad_source": 0.22, "good_source": 0.88},
        ),
    ]
    summary = build_weekly_summary(entries, window_days=7, unreliable_threshold=0.4)

    assert "bad_source" in summary["unreliable_sources"]
    assert "good_source" not in summary["unreliable_sources"]


def test_weekly_summary_stable_trend() -> None:
    from scripts.ingestion_weekly_summary import build_weekly_summary

    now = datetime.now(tz=UTC)
    entries = [
        _make_history_entry(timestamp=now - timedelta(days=4), source_scores={"src": 0.80}),
        _make_history_entry(timestamp=now - timedelta(days=3), source_scores={"src": 0.81}),
        _make_history_entry(timestamp=now - timedelta(days=2), source_scores={"src": 0.82}),
        _make_history_entry(timestamp=now - timedelta(days=1), source_scores={"src": 0.80}),
    ]
    summary = build_weekly_summary(entries, window_days=7, unreliable_threshold=0.4)

    assert summary["source_reliability"]["src"]["trend"] == "stable"


# ---------------------------------------------------------------------------
# Integration test: CLI subprocess
# ---------------------------------------------------------------------------

def test_weekly_summary_cli_writes_output(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    output_path = tmp_path / "weekly.json"
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "ingestion_weekly_window_days: 7\ningestion_unreliable_source_threshold: 0.4\n",
        encoding="utf-8",
    )

    now = datetime.now(tz=UTC)
    entry = _make_history_entry(
        timestamp=now - timedelta(days=1),
        kept_count=5,
        fetched_count=5,
        source_scores={"wiki": 0.90},
    )
    history_path.write_text(json.dumps(entry, ensure_ascii=True) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingestion_weekly_summary.py",
            "--history",
            str(history_path),
            "--output",
            str(output_path),
            "--settings",
            str(settings_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["total_runs"] == 1
    assert "wiki" in payload["source_reliability"]
    assert "Weekly summary" in result.stdout


def test_weekly_summary_history_entry_has_source_scores(tmp_path: Path) -> None:
    """Verify ingestion_scheduler.py writes source_scores into each history entry."""
    config_path = tmp_path / "sources.json"
    settings_path = tmp_path / "settings.yaml"
    output_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    history_path = tmp_path / "history.jsonl"
    drift_path = tmp_path / "drift.json"

    settings_path.write_text(
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
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "trend_source",
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

    lines = [ln for ln in history_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert "source_scores" in entry
    assert "trend_source" in entry["source_scores"]
    score = entry["source_scores"]["trend_source"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
