from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.memory_store import get_recent_memories
from training.model_registry import register_model


def build_learning_dataset(
    *,
    output_path: Path,
    merged_corpus_path: Path,
    memory_db_path: Path,
    max_memory_entries: int = 200,
    max_corpus_lines: int = 2000,
) -> dict[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    memories = get_recent_memories(limit=max_memory_entries, db_path=memory_db_path)

    corpus_lines: list[str] = []
    if merged_corpus_path.exists():
        corpus_lines = merged_corpus_path.read_text(encoding="utf-8").splitlines()[
            :max_corpus_lines
        ]

    lines: list[str] = []
    lines.extend(f"MEMORY: {entry.summary}" for entry in memories)
    lines.extend(f"CORPUS: {line.strip()}" for line in corpus_lines if line.strip())
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {
        "memory_entries": len(memories),
        "corpus_lines": len(corpus_lines),
        "total_lines": len(lines),
    }


def run_canary_evaluation(dataset_path: Path) -> dict[str, object]:
    text = dataset_path.read_text(encoding="utf-8") if dataset_path.exists() else ""
    line_count = len([line for line in text.splitlines() if line.strip()])
    char_count = len(text)
    passed = line_count >= 10 and char_count >= 200
    return {
        "passed": passed,
        "line_count": line_count,
        "char_count": char_count,
        "reason": "ok" if passed else "dataset too small for promotion",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline learning pipeline scaffold with canary gate."
    )
    parser.add_argument(
        "--memory-db", type=Path, default=ROOT / "temp" / "memory" / "memory_store.sqlite3"
    )
    parser.add_argument(
        "--merged-corpus", type=Path, default=ROOT / "temp" / "ingestion" / "merged_corpus.txt"
    )
    parser.add_argument(
        "--dataset-output", type=Path, default=ROOT / "temp" / "learning" / "learning_dataset.txt"
    )
    parser.add_argument("--registry", type=Path, default=ROOT / "runs" / "model_registry.json")
    parser.add_argument(
        "--candidate-model",
        type=Path,
        help="Path to a real model artifact to register when the canary passes.",
    )
    parser.add_argument("--promote-on-pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    # Keep script stdout machine-readable for CI/tests.
    os.environ["AI_LAN_DEBUG"] = "0"
    os.environ["AI_LAN_TRACE"] = "0"
    os.environ["AI_LAN_PROFILE"] = "0"

    args = parse_args()
    stats = build_learning_dataset(
        output_path=args.dataset_output,
        merged_corpus_path=args.merged_corpus,
        memory_db_path=args.memory_db,
    )
    canary = run_canary_evaluation(args.dataset_output)

    candidate_dir = ROOT / "temp" / "learning"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate_meta = candidate_dir / "candidate_model.meta.json"
    legacy_placeholder = candidate_dir / "candidate_model.placeholder"
    if legacy_placeholder.exists():
        legacy_placeholder.unlink()
    candidate_payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": stats,
        "canary": canary,
        "candidate_model": str(args.candidate_model) if args.candidate_model else None,
    }
    candidate_meta.write_text(
        json.dumps(candidate_payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )

    registry_record = None
    promotion_skipped_reason = None
    if canary["passed"] and args.promote_on_pass:
        if not args.candidate_model:
            promotion_skipped_reason = "no_candidate_model_artifact"
        elif args.candidate_model.suffix == ".placeholder":
            promotion_skipped_reason = "placeholder_artifacts_are_blocked"
        elif not args.candidate_model.exists():
            promotion_skipped_reason = f"candidate model not found: {args.candidate_model}"
        else:
            registry_record = register_model(
                args.candidate_model,
                metrics={"dataset_lines": float(stats["total_lines"]), "canary_pass": 1.0},
                tags=["offline", "canary-pass"],
                notes="Offline learning promotion from offline_learning_pipeline",
                registry_path=args.registry,
            )

    output = {
        "dataset_path": str(args.dataset_output),
        "candidate_meta": str(candidate_meta),
        "canary": canary,
        "registry_record": registry_record.__dict__ if registry_record else None,
        "promotion_skipped_reason": promotion_skipped_reason,
    }
    print(json.dumps(output, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
