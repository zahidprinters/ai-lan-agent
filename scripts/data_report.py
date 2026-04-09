from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from debug_utils import sentinel

from training.config import load_config
from training.corpus import analyze_file, format_report


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show corpus statistics for the active dataset.")
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Optional path to a text file. Defaults to the configured AI_LAN_DATA_PATH.",
    )
    return parser.parse_args()


@sentinel
def main() -> None:
    args = parse_args()
    config = load_config()
    data_path = args.path or config.data_path
    if not data_path.exists():
        raise SystemExit(f"Dataset not found: {data_path}")

    report = analyze_file(data_path)
    print(format_report(report))


if __name__ == "__main__":
    main()
