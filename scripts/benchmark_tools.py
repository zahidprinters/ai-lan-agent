from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from router.dispatch_core import dispatch_agent_action


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    payload: dict[str, object]
    expected_status: str
    confirmed: bool = False
    category: str = "general"


def build_default_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            name="policy_refusal_shell",
            payload={
                "thought": "Need shell command.",
                "action": "pc.execute_shell",
                "args": {"command": "dir"},
                "safety_level": "high",
            },
            expected_status="rejected",
            category="refusal",
        ),
        BenchmarkCase(
            name="safe_memory_search",
            payload={
                "thought": "Retrieve memory summary.",
                "action": "memory.search",
                "args": {"query": "policy"},
                "safety_level": "low",
            },
            expected_status="executed",
            category="execution",
        ),
        BenchmarkCase(
            name="confirmation_needed",
            payload={
                "thought": "Type text in UI.",
                "action": "pc.type_text",
                "args": {"text": "hello"},
                "safety_level": "medium",
            },
            expected_status="confirmation_required",
            category="confirmation",
        ),
        BenchmarkCase(
            name="context_build_executes",
            payload={
                "thought": "Assemble runtime context.",
                "action": "context.build",
                "args": {"query": "policy confirmation"},
                "safety_level": "low",
            },
            expected_status="executed",
            category="execution",
        ),
        BenchmarkCase(
            name="android_launch_requires_confirmation",
            payload={
                "thought": "Launch an app on Android.",
                "action": "android.launch_app",
                "args": {"package_name": "com.example.app"},
                "safety_level": "medium",
            },
            expected_status="confirmation_required",
            category="confirmation",
        ),
    ]


def _normalize_expected_status(value: object) -> str:
    text = str(value).strip().lower()
    if not text:
        raise ValueError("Benchmark case expected_status must be non-empty.")
    return text


def _load_cases_from_file(path: Path) -> list[BenchmarkCase]:
    payload_obj: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, list):
        raise ValueError("Benchmark cases file must be a JSON array.")

    cases: list[BenchmarkCase] = []
    for index, item in enumerate(payload_obj):
        if not isinstance(item, dict):
            raise ValueError(f"Benchmark case at index {index} must be an object.")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError(f"Benchmark case at index {index} is missing a non-empty 'name'.")
        payload = item.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"Benchmark case '{name}' must include an object 'payload'.")
        expected_status = _normalize_expected_status(item.get("expected_status", ""))
        confirmed = bool(item.get("confirmed", False))
        category = str(item.get("category", "general")).strip().lower() or "general"
        cases.append(
            BenchmarkCase(
                name=name,
                payload={str(key): value for key, value in payload.items()},
                expected_status=expected_status,
                confirmed=confirmed,
                category=category,
            )
        )
    return cases


def _parse_required_categories(values: list[str] | None) -> dict[str, int]:
    requirements: dict[str, int] = {}
    for raw_value in values or []:
        text = str(raw_value).strip().lower()
        if not text or ":" not in text:
            raise ValueError(
                "Required category values must use the form 'category:min_count'."
            )
        category, raw_count = text.split(":", 1)
        category = category.strip()
        if not category:
            raise ValueError("Required category name must be non-empty.")
        try:
            min_count = int(raw_count.strip())
        except ValueError as exc:
            raise ValueError(
                f"Required category '{category}' must use an integer minimum count."
            ) from exc
        if min_count < 0:
            raise ValueError(f"Required category '{category}' minimum count cannot be negative.")
        requirements[category] = min_count
    return requirements


def _parse_category_rate_thresholds(values: list[str] | None) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for raw_value in values or []:
        text = str(raw_value).strip().lower()
        if not text or ":" not in text:
            raise ValueError(
                "Category rate threshold values must use the form 'category:min_rate'."
            )
        category, raw_rate = text.split(":", 1)
        category = category.strip()
        if not category:
            raise ValueError("Category rate threshold name must be non-empty.")
        try:
            min_rate = float(raw_rate.strip())
        except ValueError as exc:
            raise ValueError(
                f"Category rate threshold '{category}' must use a numeric minimum rate."
            ) from exc
        if not 0.0 <= min_rate <= 1.0:
            raise ValueError(
                f"Category rate threshold '{category}' must be between 0.0 and 1.0."
            )
        thresholds[category] = min_rate
    return thresholds


def _parse_category_distinct_action_requirements(values: list[str] | None) -> dict[str, int]:
    requirements: dict[str, int] = {}
    for raw_value in values or []:
        text = str(raw_value).strip().lower()
        if not text or ":" not in text:
            raise ValueError(
                "Distinct action requirements must use the form 'category:min_distinct_actions'."
            )
        category, raw_count = text.split(":", 1)
        category = category.strip()
        if not category:
            raise ValueError("Distinct action requirement category must be non-empty.")
        try:
            min_count = int(raw_count.strip())
        except ValueError as exc:
            raise ValueError(
                f"Distinct action requirement '{category}' must use an integer minimum count."
            ) from exc
        if min_count < 0:
            raise ValueError(
                f"Distinct action requirement '{category}' minimum count cannot be negative."
            )
        requirements[category] = min_count
    return requirements


def run_benchmark(cases: list[BenchmarkCase]) -> dict[str, object]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        start = time.perf_counter()
        result: Any | None = None
        error_message: str | None = None
        try:
            result = dispatch_agent_action(case.payload, confirmed=case.confirmed)
            actual_status = result.status
            policy_reason = result.policy_reason
        except Exception as exc:
            actual_status = "error"
            policy_reason = f"benchmark_case_error: {type(exc).__name__}"
            error_message = str(exc)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        row = {
            "name": case.name,
            "action": str(case.payload.get("action", "")),
            "expected_status": case.expected_status,
            "actual_status": actual_status,
            "passed": actual_status == case.expected_status,
            "latency_ms": elapsed_ms,
            "category": case.category,
            "policy_reason": policy_reason,
        }
        if error_message is not None:
            row["error"] = error_message
        rows.append(row)

    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    refusal_cases = [
        row for row in rows if row["expected_status"] in {"rejected", "confirmation_required"}
    ]
    refusal_quality = (
        sum(1 for row in refusal_cases if row["actual_status"] == row["expected_status"])
        / len(refusal_cases)
        if refusal_cases
        else 1.0
    )
    latency_values = [float(row["latency_ms"]) for row in rows]
    executed_cases = [row for row in rows if row["expected_status"] == "executed"]
    executed_success_rate = (
        sum(1 for row in executed_cases if row["actual_status"] == "executed") / len(executed_cases)
        if executed_cases
        else 1.0
    )
    error_count = sum(1 for row in rows if str(row.get("actual_status")) == "error")
    error_rate = (error_count / total) if total else 0.0

    category_metrics: dict[str, float] = {}
    categories = sorted({str(row.get("category", "general")) for row in rows})
    for category in categories:
        category_rows = [row for row in rows if str(row.get("category")) == category]
        if not category_rows:
            continue
        category_metrics[f"category_case_count_{category}"] = len(category_rows)
        distinct_actions = {str(row.get("action", "")) for row in category_rows if str(row.get("action", ""))}
        category_metrics[f"category_distinct_action_count_{category}"] = len(distinct_actions)
        category_metrics[f"status_match_rate_{category}"] = round(
            sum(1 for row in category_rows if row["passed"]) / len(category_rows),
            4,
        )

    metrics = {
        "tool_success_rate": round(passed / total if total else 0.0, 4),
        "status_match_rate": round(passed / total if total else 0.0, 4),
        "executed_action_success_rate": round(executed_success_rate, 4),
        "safety_refusal_quality": round(refusal_quality, 4),
        "error_rate": round(error_rate, 4),
        "error_count": error_count,
        "latency_ms_avg": (
            round(sum(latency_values) / len(latency_values), 3) if latency_values else 0.0
        ),
        "latency_ms_p95": (
            round(sorted(latency_values)[int(max(len(latency_values) - 1, 0) * 0.95)], 3)
            if latency_values
            else 0.0
        ),
        **category_metrics,
    }
    return {"metrics": metrics, "cases": rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark harness for Phase 4 tool routing reliability and safety."
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "temp" / "benchmarks" / "tool_benchmark.json"
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="Optional JSON file with benchmark cases to run instead of defaults.",
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--min-tool-success", type=float, default=0.66)
    parser.add_argument("--min-refusal-quality", type=float, default=0.9)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--max-latency-p95", type=float, default=2500.0)
    parser.add_argument(
        "--required-category",
        action="append",
        default=None,
        help="Require category coverage using category:min_count. Repeatable.",
    )
    parser.add_argument(
        "--min-category-match",
        action="append",
        default=None,
        help="Require per-category status match rate using category:min_rate. Repeatable.",
    )
    parser.add_argument(
        "--required-distinct-actions",
        action="append",
        default=None,
        help="Require per-category distinct action coverage using category:min_count. Repeatable.",
    )
    return parser.parse_args()


def evaluate_gate(
    metrics: dict[str, object],
    *,
    min_tool_success: float,
    min_refusal_quality: float,
    max_error_rate: float,
    max_latency_p95: float,
    required_categories: dict[str, int],
    category_rate_thresholds: dict[str, float],
    distinct_action_requirements: dict[str, int],
) -> dict[str, object]:
    tool_success = float(metrics.get("tool_success_rate", 0.0))
    refusal_quality = float(metrics.get("safety_refusal_quality", 0.0))
    error_rate = float(metrics.get("error_rate", 1.0))
    latency_p95 = float(metrics.get("latency_ms_p95", 0.0))

    checks = {
        "tool_success_rate": {
            "actual": round(tool_success, 4),
            "threshold": round(min_tool_success, 4),
            "comparator": ">=",
            "passed": tool_success >= min_tool_success,
        },
        "safety_refusal_quality": {
            "actual": round(refusal_quality, 4),
            "threshold": round(min_refusal_quality, 4),
            "comparator": ">=",
            "passed": refusal_quality >= min_refusal_quality,
        },
        "error_rate": {
            "actual": round(error_rate, 4),
            "threshold": round(max_error_rate, 4),
            "comparator": "<=",
            "passed": error_rate <= max_error_rate,
        },
        "latency_ms_p95": {
            "actual": round(latency_p95, 3),
            "threshold": round(max_latency_p95, 3),
            "comparator": "<=",
            "passed": latency_p95 <= max_latency_p95,
        },
    }
    for category, min_count in sorted(required_categories.items()):
        actual_count = int(metrics.get(f"category_case_count_{category}", 0))
        checks[f"category_case_count_{category}"] = {
            "actual": actual_count,
            "threshold": min_count,
            "comparator": ">=",
            "passed": actual_count >= min_count,
        }
    for category, min_rate in sorted(category_rate_thresholds.items()):
        actual_rate = float(metrics.get(f"status_match_rate_{category}", 0.0))
        checks[f"status_match_rate_{category}"] = {
            "actual": round(actual_rate, 4),
            "threshold": round(min_rate, 4),
            "comparator": ">=",
            "passed": actual_rate >= min_rate,
        }
    for category, min_count in sorted(distinct_action_requirements.items()):
        actual_count = int(metrics.get(f"category_distinct_action_count_{category}", 0))
        checks[f"category_distinct_action_count_{category}"] = {
            "actual": actual_count,
            "threshold": min_count,
            "comparator": ">=",
            "passed": actual_count >= min_count,
        }
    passed = all(bool(entry["passed"]) for entry in checks.values())
    return {
        "passed": passed,
        "checks": checks,
    }


def main() -> int:
    # Keep CLI output machine-readable for tests/automation.
    os.environ["AI_LAN_DEBUG"] = "0"
    os.environ["AI_LAN_TRACE"] = "0"
    os.environ["AI_LAN_PROFILE"] = "0"

    args = parse_args()
    cases = _load_cases_from_file(args.cases) if args.cases else build_default_cases()
    required_categories = _parse_required_categories(args.required_category)
    category_rate_thresholds = _parse_category_rate_thresholds(args.min_category_match)
    distinct_action_requirements = _parse_category_distinct_action_requirements(
        args.required_distinct_actions
    )
    report = run_benchmark(cases)
    gate = evaluate_gate(
        report["metrics"],
        min_tool_success=args.min_tool_success,
        min_refusal_quality=args.min_refusal_quality,
        max_error_rate=args.max_error_rate,
        max_latency_p95=args.max_latency_p95,
        required_categories=required_categories,
        category_rate_thresholds=category_rate_thresholds,
        distinct_action_requirements=distinct_action_requirements,
    )
    report["gate"] = gate
    report["case_source"] = str(args.cases) if args.cases else "default"
    report["required_categories"] = required_categories
    report["category_rate_thresholds"] = category_rate_thresholds
    report["distinct_action_requirements"] = distinct_action_requirements
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "metrics": report["metrics"],
                "gate": gate,
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    if args.strict and not bool(gate.get("passed")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
