from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel


def _coerce_scalar(raw_value: str) -> object:
    normalized = raw_value.strip()
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"1", "0"}:
        return lowered == "1"
    try:
        if any(char in normalized for char in {".", "e", "E"}):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized.strip('"').strip("'")


def _load_settings_values(settings_path: Path) -> dict[str, object]:
    if not settings_path.exists():
        return {}
    values: dict[str, object] = {}
    for raw_line in settings_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)
    return values


def _load_history(history_path: Path) -> list[dict[str, object]]:
    if not history_path.exists():
        return []
    entries: list[dict[str, object]] = []
    for raw_line in history_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append({str(k): v for k, v in parsed.items()})
    return entries


def _filter_by_window(
    entries: list[dict[str, object]], window_days: int
) -> list[dict[str, object]]:
    if window_days <= 0:
        return list(entries)
    cutoff = datetime.now(tz=UTC) - timedelta(days=window_days)
    result: list[dict[str, object]] = []
    for entry in entries:
        ts_raw = entry.get("timestamp")
        if not isinstance(ts_raw, str):
            continue
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            else:
                ts = ts.astimezone(UTC)
        except ValueError:
            continue
        if ts >= cutoff:
            result.append(entry)
    return result


def _trend_direction(scores: list[float]) -> str:
    """Return 'improving', 'degrading', or 'stable' based on first vs second half averages."""
    if len(scores) < 2:
        return "stable"
    mid = max(1, len(scores) // 2)
    first_half = scores[:mid]
    second_half = scores[mid:]
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    delta = second_avg - first_avg
    if delta >= 0.05:
        return "improving"
    if delta <= -0.05:
        return "degrading"
    return "stable"


def _build_source_reliability(
    entries: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Aggregate per-source final scores across history entries."""
    source_history: dict[str, list[float]] = {}
    for entry in entries:
        source_scores = entry.get("source_scores")
        if not isinstance(source_scores, dict):
            continue
        for name, score_raw in source_scores.items():
            if isinstance(score_raw, (int, float)):
                source_history.setdefault(str(name), []).append(float(score_raw))

    result: dict[str, dict[str, object]] = {}
    for name, scores in source_history.items():
        avg = round(sum(scores) / len(scores), 3)
        result[name] = {
            "run_count": len(scores),
            "avg_final_score": avg,
            "min_final_score": round(min(scores), 3),
            "max_final_score": round(max(scores), 3),
            "trend": _trend_direction(scores),
        }
    return result


@sentinel
def build_weekly_summary(
    entries: list[dict[str, object]],
    *,
    window_days: int,
    unreliable_threshold: float,
) -> dict[str, object]:
    """Produce a weekly health summary from a list of history entries."""
    windowed = _filter_by_window(entries, window_days)

    profile_counts: dict[str, int] = {}
    drift_counts: dict[str, int] = {}
    kept_totals: list[int] = []
    fetched_totals: list[int] = []

    for entry in windowed:
        profile = str(entry.get("profile_name", "unknown"))
        profile_counts[profile] = profile_counts.get(profile, 0) + 1

        drift_status = str(entry.get("drift_status", "unknown"))
        drift_counts[drift_status] = drift_counts.get(drift_status, 0) + 1

        metrics = entry.get("metrics")
        if isinstance(metrics, dict):
            kept = metrics.get("kept_count")
            fetched = metrics.get("fetched_count")
            if isinstance(kept, (int, float)):
                kept_totals.append(int(kept))
            if isinstance(fetched, (int, float)):
                fetched_totals.append(int(fetched))

    source_reliability = _build_source_reliability(windowed)
    unreliable_sources = [
        name
        for name, info in source_reliability.items()
        if float(info.get("avg_final_score", 1.0)) < unreliable_threshold
    ]

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "window_days": window_days,
        "total_runs": len(windowed),
        "profile_run_counts": profile_counts,
        "drift_status_counts": drift_counts,
        "avg_kept_per_run": (
            round(sum(kept_totals) / len(kept_totals), 2) if kept_totals else 0.0
        ),
        "avg_fetched_per_run": (
            round(sum(fetched_totals) / len(fetched_totals), 2) if fetched_totals else 0.0
        ),
        "source_reliability": source_reliability,
        "unreliable_sources": unreliable_sources,
        "unreliable_source_threshold": round(float(unreliable_threshold), 3),
    }


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a weekly ingestion health summary from JSONL run history."
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "ingestion_report_history.jsonl",
        help="JSONL history file written by ingestion_scheduler.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "ingestion_weekly_summary.json",
        help="Output path for the weekly summary JSON.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=ROOT / "config" / "settings.yaml",
        help="Settings YAML path for threshold defaults.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="Days to look back (default from settings or 7).",
    )
    parser.add_argument(
        "--unreliable-threshold",
        type=float,
        default=None,
        help="Avg final score below which a source is flagged (default from settings or 0.4).",
    )
    return parser.parse_args()


@sentinel
def main() -> int:
    args = parse_args()

    settings_values = _load_settings_values(args.settings)

    window_days = (
        args.window_days
        if args.window_days is not None
        else int(settings_values.get("ingestion_weekly_window_days", 7))
    )
    unreliable_threshold = (
        args.unreliable_threshold
        if args.unreliable_threshold is not None
        else float(settings_values.get("ingestion_unreliable_source_threshold", 0.4))
    )

    entries = _load_history(args.history)
    summary = build_weekly_summary(
        entries,
        window_days=window_days,
        unreliable_threshold=unreliable_threshold,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(f"Weekly summary: {summary['total_runs']} runs in last {window_days}d")
    if summary["unreliable_sources"]:
        print(f"Unreliable sources ({len(summary['unreliable_sources'])}): {summary['unreliable_sources']}")
    else:
        print("No unreliable sources flagged.")
    print(f"Summary written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
