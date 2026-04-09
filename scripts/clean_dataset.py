from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from debug_utils import sentinel

from training.config import load_config


@sentinel
def clean_lines(lines: list[str]) -> list[str]:
    # Remove empty lines, strip whitespace, deduplicate
    seen = set()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line in seen:
            continue
        seen.add(line)
        cleaned.append(line)
    return cleaned


@sentinel
def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and deduplicate a text dataset.")
    parser.add_argument(
        "--input", type=Path, default=None, help="Input text file (default: config data path)"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Output file (default: input_cleaned.txt)"
    )
    args = parser.parse_args()

    config = load_config()
    input_path = args.input or config.data_path
    output_path = args.output or input_path.with_name(input_path.stem + "_cleaned.txt")

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    cleaned = clean_lines(lines)
    output_path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    print(f"Cleaned dataset written to: {output_path}")
    print(f"Original lines: {len(lines)} | Cleaned lines: {len(cleaned)}")


if __name__ == "__main__":
    main()
