from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel
from tools.storage_health import run_storage_cleanup, write_cleanup_report


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean aged temporary storage artifacts with retention-policy safety defaults."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletion. Default is dry-run mode with no file deletion.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=ROOT / "config" / "settings.yaml",
        help="Path to settings YAML with storage retention keys.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "storage_cleanup_report.json",
        help="Output path for JSON cleanup report.",
    )
    return parser.parse_args()


@sentinel
def main() -> int:
    args = parse_args()
    dry_run = not args.apply
    plan = run_storage_cleanup(
        dry_run=dry_run,
        project_root=ROOT,
        settings_path=args.settings,
    )
    write_cleanup_report(args.report, plan)

    print(json.dumps(plan.to_dict(), ensure_ascii=True, indent=2))
    print(f"Report output: {args.report}")
    if dry_run:
        print("Mode: dry-run (no files deleted)")
    else:
        print("Mode: apply (old files deleted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
