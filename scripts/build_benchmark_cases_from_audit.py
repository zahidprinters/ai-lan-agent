from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SUPPORTED_STATUSES = {"executed", "rejected", "confirmation_required"}


@dataclass(frozen=True)
class DerivedBenchmarkCase:
    name: str
    payload: dict[str, Any]
    expected_status: str
    confirmed: bool
    category: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _infer_category(status: str) -> str:
    if status == "executed":
        return "execution"
    if status == "rejected":
        return "refusal"
    if status == "confirmation_required":
        return "confirmation"
    return "general"


def _normalize_status(value: object) -> str:
    return str(value or "").strip().lower()


def _stable_case_key(request: dict[str, Any], expected_status: str, confirmed: bool) -> str:
    return json.dumps(
        {
            "action": request.get("action"),
            "args": request.get("args", {}),
            "safety_level": request.get("safety_level"),
            "expected_status": expected_status,
            "confirmed": confirmed,
        },
        ensure_ascii=True,
        sort_keys=True,
    )


def build_cases_from_audit(
    input_path: Path,
    *,
    max_cases: int | None = None,
) -> list[DerivedBenchmarkCase]:
    if not input_path.exists():
        raise FileNotFoundError(f"Audit log not found: {input_path}")

    rows = input_path.read_text(encoding="utf-8").splitlines()
    cases: list[DerivedBenchmarkCase] = []
    seen: set[str] = set()
    ordinal = 0

    for line in rows:
        if not line.strip():
            continue
        payload = json.loads(line)
        request = payload.get("request")
        result = payload.get("result")
        if not isinstance(request, dict) or not isinstance(result, dict):
            continue

        expected_status = _normalize_status(result.get("status"))
        if expected_status not in SUPPORTED_STATUSES:
            continue

        request_payload = {str(key): value for key, value in request.items()}
        confirmed = expected_status == "executed"
        dedupe_key = _stable_case_key(request_payload, expected_status, confirmed)
        if dedupe_key in seen:
            continue

        action_name = str(request_payload.get("action", "action")).replace(".", "_")
        category = _infer_category(expected_status)
        ordinal += 1
        cases.append(
            DerivedBenchmarkCase(
                name=f"audit_{ordinal:03d}_{action_name}_{expected_status}",
                payload=request_payload,
                expected_status=expected_status,
                confirmed=confirmed,
                category=category,
            )
        )
        seen.add(dedupe_key)

        if max_cases is not None and len(cases) >= max_cases:
            break

    return cases


def write_cases(output_path: Path, cases: list[DerivedBenchmarkCase]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([case.to_dict() for case in cases], indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Derive benchmark case JSON from action audit logs for trace-based Phase 4.3 eval coverage."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "temp" / "action_audit.jsonl",
        help="Path to action audit JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "trace_benchmark_cases.json",
        help="Path to write derived benchmark cases JSON.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=25,
        help="Maximum number of deduplicated cases to emit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = build_cases_from_audit(args.input, max_cases=args.max_cases)
    write_cases(args.output, cases)
    print(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "case_count": len(cases),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())