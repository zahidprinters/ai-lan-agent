from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel
from tools.web_ingest import load_ingestion_sources, run_ingestion_pipeline


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
        "--min-final-score",
        type=float,
        default=0.3,
        help="Minimum final score required to keep a source document (0.0 to 1.0).",
    )
    return parser.parse_args()


@sentinel
def main() -> None:
    args = parse_args()
    sources = load_ingestion_sources(args.config)
    report = run_ingestion_pipeline(
        sources,
        merged_output_path=args.output,
        report_output_path=args.report,
        min_final_score=args.min_final_score,
    )
    print(f"Ingestion sources: {report.source_count}")
    print(f"Documents kept: {report.kept_count}")
    print(f"Filtered low score: {report.filtered_low_score_count}")
    print(f"Duplicates dropped: {report.duplicate_count}")
    print(f"Merged lines: {report.merged_line_count}")
    print(f"Merged output: {args.output}")
    print(f"Report output: {args.report}")


if __name__ == "__main__":
    main()
