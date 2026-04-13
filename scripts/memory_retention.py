from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel
from tools.memory_store import prune_memory_entries, resolve_memory_max_entries, resolve_memory_retention_days


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


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run memory retention pruning and write a machine-readable report."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite memory store (default: temp/memory/memory_store.sqlite3).",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=ROOT / "config" / "settings.yaml",
        help="Settings YAML for retention_days and max_entries defaults.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "memory_retention_report.json",
        help="Output path for the retention report JSON.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="Override memory retention days (default: from settings or 30).",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        help="Override maximum memory entries (default: from settings or 2000).",
    )
    parser.add_argument(
        "--kind",
        type=str,
        default=None,
        help="Limit pruning to a specific memory kind (e.g. 'conversation').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report candidates without deleting anything.",
    )
    return parser.parse_args()


@sentinel
def main() -> int:
    args = parse_args()

    settings_values = _load_settings_values(args.settings)

    retention_days = (
        args.retention_days
        if args.retention_days is not None
        else int(settings_values.get("memory_retention_days", 30))
    )
    max_entries = (
        args.max_entries
        if args.max_entries is not None
        else int(settings_values.get("memory_max_entries", 2000))
    )

    result = prune_memory_entries(
        db_path=args.db,
        retention_days=retention_days,
        max_entries=max_entries,
        kind=args.kind,
        dry_run=args.dry_run,
    )

    report: dict[str, object] = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "dry_run": args.dry_run,
        **result,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    action = "DRY RUN —" if args.dry_run else "Pruned"
    print(
        f"{action} {result['pruned_count']} entries "
        f"(age_candidates={result['age_candidates']}, "
        f"overflow_candidates={result['overflow_candidates']})"
    )
    print(f"Retention report written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
