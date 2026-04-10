from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_PROMPTS_PATH = ROOT / "data" / "benchmarks" / "quality_prompts.json"
DEFAULT_OUTPUT_DIR = ROOT / "runs" / "quality"


def _load_prompt_suite(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Prompt suite must be a JSON list.")
    prompts: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            prompts.append({str(key): value for key, value in item.items()})
    if not prompts:
        raise ValueError("Prompt suite is empty.")
    return prompts


def _resolve_score(args: argparse.Namespace) -> tuple[float, str]:
    if args.score is not None:
        return float(args.score), "manual"
    if args.metrics_json is not None:
        metrics_obj = json.loads(args.metrics_json.read_text(encoding="utf-8"))
        if isinstance(metrics_obj, dict) and isinstance(metrics_obj.get("quality_score"), (int, float)):
            return float(metrics_obj["quality_score"]), "metrics_json"
        raise ValueError("Metrics JSON must include numeric 'quality_score'.")
    return 0.0, "default_zero"


def _build_output_path(output_dir: Path, model_path: Path, version: str | None) -> Path:
    identifier = version or model_path.stem
    safe_identifier = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in identifier)
    return output_dir / f"{safe_identifier}_quality.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persist quality benchmark artifacts for promotion guardrails.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--score", type=float, default=None)
    parser.add_argument("--metrics-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompts = _load_prompt_suite(args.prompts)
    score, score_source = _resolve_score(args)
    output_path = _build_output_path(args.output_dir, args.model, args.version.strip() or None)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(args.model),
        "model_version": args.version.strip() or None,
        "prompt_suite_path": str(args.prompts),
        "prompt_count": len(prompts),
        "score": round(score, 4),
        "score_source": score_source,
    }
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "artifact": artifact}, indent=2, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())