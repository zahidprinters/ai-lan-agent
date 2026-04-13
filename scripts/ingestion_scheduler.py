from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


def _load_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return {str(key): value for key, value in payload.items()}


def _average_final_score(report: dict[str, object]) -> float:
    documents_obj = report.get("documents")
    if not isinstance(documents_obj, list) or not documents_obj:
        return 0.0
    scores: list[float] = []
    for document in documents_obj:
        if not isinstance(document, dict):
            continue
        score_raw = document.get("final_score")
        if isinstance(score_raw, (int, float)):
            scores.append(float(score_raw))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def _metrics_from_report(report: dict[str, object]) -> dict[str, float | int]:
    return {
        "source_count": int(report.get("source_count", 0)),
        "fetched_count": int(report.get("fetched_count", 0)),
        "kept_count": int(report.get("kept_count", 0)),
        "filtered_low_score_count": int(report.get("filtered_low_score_count", 0)),
        "duplicate_count": int(report.get("duplicate_count", 0)),
        "average_final_score": _average_final_score(report),
    }


def _source_scores_from_report(report: dict[str, object]) -> dict[str, float]:
    """Extract the latest final_score for each named source from a report's documents list."""
    documents_obj = report.get("documents")
    if not isinstance(documents_obj, list):
        return {}
    scores: dict[str, float] = {}
    for document in documents_obj:
        if not isinstance(document, dict):
            continue
        name_raw = document.get("name")
        score_raw = document.get("final_score")
        if isinstance(name_raw, str) and isinstance(score_raw, (int, float)):
            scores[name_raw] = round(float(score_raw), 3)
    return scores


def _load_last_history_entry(history_path: Path) -> dict[str, object] | None:
    if not history_path.exists():
        return None
    lines = [line.strip() for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    payload = json.loads(lines[-1])
    if not isinstance(payload, dict):
        return None
    return {str(key): value for key, value in payload.items()}


def _build_drift_report(
    *,
    current_metrics: dict[str, float | int],
    baseline_metrics: dict[str, float | int] | None,
    kept_drop_warn: int,
    avg_score_drop_warn: float,
) -> dict[str, object]:
    if baseline_metrics is None:
        return {
            "status": "no_baseline",
            "warnings": [],
            "current_metrics": current_metrics,
            "baseline_metrics": None,
            "deltas": {},
        }

    kept_delta = int(current_metrics["kept_count"]) - int(baseline_metrics["kept_count"])
    avg_delta = round(
        float(current_metrics["average_final_score"]) - float(baseline_metrics["average_final_score"]),
        3,
    )

    warnings: list[str] = []
    if (-kept_delta) >= kept_drop_warn:
        warnings.append("kept_count_drop")
    if (-avg_delta) >= avg_score_drop_warn:
        warnings.append("average_final_score_drop")

    status = "warn" if warnings else "ok"
    return {
        "status": status,
        "warnings": warnings,
        "current_metrics": current_metrics,
        "baseline_metrics": baseline_metrics,
        "deltas": {
            "kept_count": kept_delta,
            "average_final_score": avg_delta,
        },
    }


def _append_history(
    *,
    history_path: Path,
    report_path: Path,
    profile_name: str,
    metrics: dict[str, float | int],
    drift_status: str,
    source_scores: dict[str, float] | None = None,
) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, object] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "report_path": str(report_path),
        "profile_name": profile_name,
        "metrics": metrics,
        "drift_status": drift_status,
        "source_scores": source_scores if source_scores is not None else {},
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run profile-based ingestion and emit drift/history benchmark reports."
    )
    parser.add_argument("--config", type=Path, required=True, help="Ingestion sources JSON path.")
    parser.add_argument(
        "--settings",
        type=Path,
        default=ROOT / "config" / "settings.yaml",
        help="Settings file for profile defaults and drift thresholds.",
    )
    parser.add_argument(
        "--profile",
        choices=["fast", "daily", "deep"],
        default=None,
        help="Optional scheduler profile override.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "ingestion" / "merged_corpus.txt",
        help="Merged corpus output path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "temp" / "ingestion" / "ingestion_report.json",
        help="Ingestion report output path.",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "ingestion_report_history.jsonl",
        help="JSONL history of ingestion benchmark metrics.",
    )
    parser.add_argument(
        "--drift-report",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "ingestion_drift_report.json",
        help="JSON output path for latest drift analysis.",
    )
    parser.add_argument(
        "--min-final-score",
        type=float,
        default=None,
        help="Optional override forwarded to ingestion pipeline.",
    )
    parser.add_argument(
        "--freshness-half-life-days",
        type=float,
        default=None,
        help="Optional override forwarded to ingestion pipeline.",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Optional ISO timestamp for deterministic freshness scoring.",
    )
    parser.add_argument(
        "--drift-kept-drop-warn",
        type=int,
        default=None,
        help="Warn when kept_count drops by this amount or more.",
    )
    parser.add_argument(
        "--drift-avg-score-drop-warn",
        type=float,
        default=None,
        help="Warn when average final score drops by this value or more.",
    )
    return parser.parse_args()


@sentinel
def main() -> int:
    args = parse_args()

    settings_values = _load_settings_values(args.settings)
    kept_drop_warn = int(
        args.drift_kept_drop_warn
        if args.drift_kept_drop_warn is not None
        else settings_values.get("ingestion_drift_kept_drop_warn", 2)
    )
    avg_score_drop_warn = float(
        args.drift_avg_score_drop_warn
        if args.drift_avg_score_drop_warn is not None
        else settings_values.get("ingestion_drift_avg_final_score_drop_warn", 0.08)
    )

    existing_report = _load_json(args.report)
    baseline_metrics: dict[str, float | int] | None = (
        _metrics_from_report(existing_report) if existing_report is not None else None
    )
    if baseline_metrics is None:
        last_history_entry = _load_last_history_entry(args.history)
        metrics_obj: Any = last_history_entry.get("metrics") if last_history_entry else None
        if isinstance(metrics_obj, dict):
            baseline_metrics = {
                str(key): casted
                for key, casted in metrics_obj.items()
                if isinstance(casted, (int, float))
            }

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "ingest_sources.py"),
        "--config",
        str(args.config),
        "--settings",
        str(args.settings),
        "--output",
        str(args.output),
        "--report",
        str(args.report),
    ]
    if args.profile is not None:
        cmd.extend(["--profile", args.profile])
    if args.min_final_score is not None:
        cmd.extend(["--min-final-score", str(args.min_final_score)])
    if args.freshness_half_life_days is not None:
        cmd.extend(["--freshness-half-life-days", str(args.freshness_half_life_days)])
    if args.as_of is not None:
        cmd.extend(["--as-of", args.as_of])

    run_result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    if run_result.stdout.strip():
        print(run_result.stdout.strip())
    if run_result.stderr.strip():
        print(run_result.stderr.strip())

    current_report = _load_json(args.report)
    if current_report is None:
        raise ValueError("Ingestion report missing after scheduler run.")

    current_metrics = _metrics_from_report(current_report)
    drift = _build_drift_report(
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        kept_drop_warn=max(1, kept_drop_warn),
        avg_score_drop_warn=max(0.0, avg_score_drop_warn),
    )
    drift["generated_at"] = datetime.now(tz=UTC).isoformat()
    drift["kept_drop_warn_threshold"] = max(1, kept_drop_warn)
    drift["avg_score_drop_warn_threshold"] = max(0.0, avg_score_drop_warn)
    args.drift_report.parent.mkdir(parents=True, exist_ok=True)
    args.drift_report.write_text(json.dumps(drift, indent=2, ensure_ascii=True), encoding="utf-8")

    profile_name = str(current_report.get("profile_name", "unknown"))
    source_scores = _source_scores_from_report(current_report)
    _append_history(
        history_path=args.history,
        report_path=args.report,
        profile_name=profile_name,
        metrics=current_metrics,
        drift_status=str(drift["status"]),
        source_scores=source_scores,
    )

    print(f"Drift status: {drift['status']}")
    print(f"Drift report: {args.drift_report}")
    print(f"History output: {args.history}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())