from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel
from tools.web_ingest import load_ingestion_sources, run_ingestion_pipeline


@dataclass(frozen=True)
class IngestionSchedulerProfile:
    name: str
    min_final_score: float
    freshness_half_life_days: float


DEFAULT_PROFILES: dict[str, IngestionSchedulerProfile] = {
    "fast": IngestionSchedulerProfile(
        name="fast",
        min_final_score=0.25,
        freshness_half_life_days=45.0,
    ),
    "daily": IngestionSchedulerProfile(
        name="daily",
        min_final_score=0.3,
        freshness_half_life_days=30.0,
    ),
    "deep": IngestionSchedulerProfile(
        name="deep",
        min_final_score=0.4,
        freshness_half_life_days=14.0,
    ),
}


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


def _load_settings_values(settings_path: Path | None) -> dict[str, object]:
    if settings_path is None:
        return {}
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


def _profile_from_settings(
    settings_values: dict[str, object],
    profile_name: str,
) -> IngestionSchedulerProfile:
    score_key = f"ingestion_min_final_score_{profile_name}"
    freshness_key = f"ingestion_freshness_half_life_days_{profile_name}"
    min_final_score = float(settings_values.get(score_key, DEFAULT_PROFILES[profile_name].min_final_score))
    freshness_half_life_days = float(
        settings_values.get(
            freshness_key,
            DEFAULT_PROFILES[profile_name].freshness_half_life_days,
        )
    )
    return IngestionSchedulerProfile(
        name=profile_name,
        min_final_score=min_final_score,
        freshness_half_life_days=freshness_half_life_days,
    )


def _parse_as_of_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def resolve_scheduler_profile(args: argparse.Namespace) -> IngestionSchedulerProfile:
    settings_values = _load_settings_values(args.settings)
    default_profile = str(settings_values.get("ingestion_profile_default", "daily")).strip().lower()

    selected_name = (args.profile or default_profile).strip().lower()
    if selected_name not in DEFAULT_PROFILES:
        supported = ", ".join(sorted(DEFAULT_PROFILES))
        raise ValueError(f"Unsupported scheduler profile '{selected_name}'. Supported: {supported}")

    profile = _profile_from_settings(settings_values, selected_name)
    if args.min_final_score is not None:
        profile = IngestionSchedulerProfile(
            name=profile.name,
            min_final_score=args.min_final_score,
            freshness_half_life_days=profile.freshness_half_life_days,
        )
    if args.freshness_half_life_days is not None:
        profile = IngestionSchedulerProfile(
            name=profile.name,
            min_final_score=profile.min_final_score,
            freshness_half_life_days=args.freshness_half_life_days,
        )
    return profile


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch, score, dedupe, and merge trusted text sources."
    )
    parser.add_argument(
        "--config", type=Path, required=True, help="JSON array describing input sources."
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
        help="JSON report output path.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=ROOT / "config" / "settings.yaml",
        help="Optional settings file for profile defaults and overrides.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(DEFAULT_PROFILES),
        default=None,
        help="Scheduler profile: fast, daily, or deep.",
    )
    parser.add_argument(
        "--min-final-score",
        type=float,
        default=None,
        help="Override minimum final score required to keep a document (0.0 to 1.0).",
    )
    parser.add_argument(
        "--freshness-half-life-days",
        type=float,
        default=None,
        help="Override freshness decay half-life in days.",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Optional ISO timestamp for deterministic freshness scoring.",
    )
    return parser.parse_args()


@sentinel
def main() -> None:
    args = parse_args()
    sources = load_ingestion_sources(args.config)
    profile = resolve_scheduler_profile(args)
    as_of = _parse_as_of_timestamp(args.as_of)
    report = run_ingestion_pipeline(
        sources,
        merged_output_path=args.output,
        report_output_path=args.report,
        min_final_score=profile.min_final_score,
        freshness_half_life_days=profile.freshness_half_life_days,
        profile_name=profile.name,
        as_of=as_of,
    )
    print(f"Scheduler profile: {profile.name}")
    print(f"Freshness half-life days: {profile.freshness_half_life_days}")
    print(f"Min final score: {profile.min_final_score}")
    print(f"Ingestion sources: {report.source_count}")
    print(f"Documents kept: {report.kept_count}")
    print(f"Filtered low score: {report.filtered_low_score_count}")
    print(f"Duplicates dropped: {report.duplicate_count}")
    print(f"Merged lines: {report.merged_line_count}")
    print(f"Merged output: {args.output}")
    print(f"Report output: {args.report}")


if __name__ == "__main__":
    main()
