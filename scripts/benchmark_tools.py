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

from agents.react.runtime_guard import (
    build_execution_contract,
    evaluate_runtime_dispatch_guard,
    verify_execution_contract,
)
from core.inference.context_manager import compact_prompt_context
from core.inference.kv_cache_manager import KVCachePolicy
from core.inference.model_router import ReasoningModelRouter
from router.dispatch_core import dispatch_agent_action


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    payload: dict[str, object]
    expected_status: str
    confirmed: bool = False
    category: str = "general"
    planner_metadata: dict[str, object] | None = None
    expected_guard_allowed: bool | None = None
    expected_execution_contract_valid: bool | None = None
    expected_execution_contract_reason: str | None = None
    autobuild_execution_contract: bool = False
    routing_probe: dict[str, object] | None = None
    compaction_probe: dict[str, object] | None = None


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
        planner_metadata_obj = item.get("planner_metadata")
        planner_metadata = (
            {str(key): value for key, value in planner_metadata_obj.items()}
            if isinstance(planner_metadata_obj, dict)
            else None
        )
        expected_guard_allowed_obj = item.get("expected_guard_allowed")
        expected_guard_allowed = (
            bool(expected_guard_allowed_obj)
            if isinstance(expected_guard_allowed_obj, bool)
            else None
        )
        expected_execution_contract_valid_obj = item.get("expected_execution_contract_valid")
        expected_execution_contract_valid = (
            bool(expected_execution_contract_valid_obj)
            if isinstance(expected_execution_contract_valid_obj, bool)
            else None
        )
        expected_execution_contract_reason = str(
            item.get("expected_execution_contract_reason", "")
        ).strip() or None
        autobuild_execution_contract = bool(item.get("autobuild_execution_contract", False))
        routing_probe_obj = item.get("routing_probe")
        routing_probe = (
            {str(key): value for key, value in routing_probe_obj.items()}
            if isinstance(routing_probe_obj, dict)
            else None
        )
        compaction_probe_obj = item.get("compaction_probe")
        compaction_probe = (
            {str(key): value for key, value in compaction_probe_obj.items()}
            if isinstance(compaction_probe_obj, dict)
            else None
        )
        cases.append(
            BenchmarkCase(
                name=name,
                payload={str(key): value for key, value in payload.items()},
                expected_status=expected_status,
                confirmed=confirmed,
                category=category,
                planner_metadata=planner_metadata,
                expected_guard_allowed=expected_guard_allowed,
                expected_execution_contract_valid=expected_execution_contract_valid,
                expected_execution_contract_reason=expected_execution_contract_reason,
                autobuild_execution_contract=autobuild_execution_contract,
                routing_probe=routing_probe,
                compaction_probe=compaction_probe,
            )
        )
    return cases


def _evaluate_execution_contract_assertion(
    case: BenchmarkCase,
    guard_decision: Any,
) -> tuple[bool | None, str | None]:
    if case.expected_execution_contract_valid is None:
        return None, None

    metadata = dict(case.planner_metadata or {})
    runtime_guard_obj = metadata.get("runtime_guard")
    if not isinstance(runtime_guard_obj, dict):
        runtime_guard_obj = guard_decision.to_dict()
        metadata["runtime_guard"] = runtime_guard_obj

    if case.autobuild_execution_contract and "execution_contract" not in metadata:
        if "stream_trigger_mode" in metadata and "stream_trigger_payload" not in metadata:
            metadata["stream_trigger_payload"] = dict(case.payload)
        metadata["execution_contract"] = build_execution_contract(
            action_payload=case.payload,
            metadata=metadata,
            runtime_guard=guard_decision,
        )

    verification = verify_execution_contract(action_payload=case.payload, metadata=metadata)
    matches = verification.valid == case.expected_execution_contract_valid
    if case.expected_execution_contract_reason is not None:
        matches = matches and verification.reason == case.expected_execution_contract_reason
    return matches, verification.reason


def _evaluate_routing_probe(case: BenchmarkCase) -> tuple[bool | None, dict[str, object] | None]:
    if not isinstance(case.routing_probe, dict):
        return None, None

    router_config = case.routing_probe.get("router")
    router_kwargs = dict(router_config) if isinstance(router_config, dict) else {}
    for key in ("simple_model_path", "complex_model_path", "explicit_model_path"):
        value = router_kwargs.get(key)
        if isinstance(value, str) and value.strip():
            router_kwargs[key] = Path(value)

    router = ReasoningModelRouter(**router_kwargs)
    requested_model_path = case.routing_probe.get("requested_model_path")
    requested_path = Path(str(requested_model_path)) if isinstance(requested_model_path, str) else None
    plan = router.build_plan(
        task_complexity=str(case.routing_probe.get("task_complexity", "complex")),
        pressure_high=bool(case.routing_probe.get("pressure_high", False)),
        requested_model_path=requested_path,
    )
    actual = {
        "primary_selection_reason": plan.primary.selection_reason,
        "primary_resident_enabled": plan.primary.resident_enabled,
        "candidate_count": len(plan.candidates),
    }
    expected = case.routing_probe.get("expected")
    if not isinstance(expected, dict):
        return None, actual

    matches = True
    if "primary_selection_reason" in expected:
        matches = matches and actual["primary_selection_reason"] == str(expected["primary_selection_reason"])
    if "primary_resident_enabled" in expected:
        matches = matches and actual["primary_resident_enabled"] == bool(expected["primary_resident_enabled"])
    if "candidate_count" in expected:
        matches = matches and actual["candidate_count"] == int(expected["candidate_count"])
    return matches, actual


def _evaluate_compaction_probe(case: BenchmarkCase) -> tuple[bool | None, dict[str, object] | None]:
    if not isinstance(case.compaction_probe, dict):
        return None, None

    runtime_context_value = case.compaction_probe.get("runtime_context")
    runtime_context = (
        {"assembled_context": str(runtime_context_value)} if runtime_context_value is not None else None
    )
    policy_obj = case.compaction_probe.get("policy")
    policy = KVCachePolicy(**policy_obj) if isinstance(policy_obj, dict) else None
    recent_turns = case.compaction_probe.get("recent_turns")
    recent_thoughts = case.compaction_probe.get("recent_thoughts")
    recent_observations = case.compaction_probe.get("recent_observations")
    compacted = compact_prompt_context(
        runtime_context=runtime_context,
        recent_turns=recent_turns if isinstance(recent_turns, list) else None,
        recent_thoughts=recent_thoughts if isinstance(recent_thoughts, list) else None,
        recent_observations=recent_observations if isinstance(recent_observations, list) else None,
        policy=policy,
    )
    actual = {
        "compacted": compacted.compacted,
        "runtime_context_text": compacted.runtime_context_text,
        "summary_blocks": compacted.summary_blocks,
    }

    matches = True
    if "expected_compacted" in case.compaction_probe:
        matches = matches and compacted.compacted == bool(case.compaction_probe["expected_compacted"])
    runtime_context_contains = case.compaction_probe.get("runtime_context_contains")
    if isinstance(runtime_context_contains, list):
        matches = matches and all(
            str(fragment) in compacted.runtime_context_text for fragment in runtime_context_contains
        )
    summary_contains = case.compaction_probe.get("summary_contains")
    if isinstance(summary_contains, list):
        combined_summary = "\n".join(compacted.summary_blocks)
        matches = matches and all(str(fragment) in combined_summary for fragment in summary_contains)
    return matches, actual


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


def _probe_failure_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    probe_specs = {
        "runtime_guard": {
            "match_field": "runtime_guard_expected_match",
            "reason_field": "runtime_guard_reason",
        },
        "execution_contract": {
            "match_field": "execution_contract_match",
            "reason_field": "execution_contract_reason",
        },
        "routing_assertion": {
            "match_field": "routing_probe_match",
            "reason_field": None,
        },
        "compaction_assertion": {
            "match_field": "compaction_probe_match",
            "reason_field": None,
        },
    }

    summary: dict[str, dict[str, object]] = {}
    for probe_name, spec in probe_specs.items():
        match_field = str(spec["match_field"])
        reason_field = spec["reason_field"]
        evaluated_rows = [row for row in rows if isinstance(row.get(match_field), bool)]
        failed_rows = [row for row in evaluated_rows if not bool(row.get(match_field))]
        reasons: dict[str, int] = {}
        if isinstance(reason_field, str):
            for row in failed_rows:
                reason = str(row.get(reason_field, "unknown")).strip() or "unknown"
                reasons[reason] = reasons.get(reason, 0) + 1

        summary[probe_name] = {
            "evaluated_count": len(evaluated_rows),
            "failed_count": len(failed_rows),
            "failed_cases": [str(row.get("name", "")) for row in failed_rows[:5]],
            "failure_reasons": dict(sorted(reasons.items())),
        }
    return summary


def run_benchmark(cases: list[BenchmarkCase]) -> dict[str, object]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        start = time.perf_counter()
        result: Any | None = None
        error_message: str | None = None
        guard_decision = evaluate_runtime_dispatch_guard(
            action_payload=case.payload,
            metadata=case.planner_metadata,
        )
        try:
            if not guard_decision.allowed:
                actual_status = "rejected"
                policy_reason = f"runtime_guard:{guard_decision.reason}"
            else:
                result = dispatch_agent_action(case.payload, confirmed=case.confirmed)
                actual_status = result.status
                policy_reason = result.policy_reason
        except Exception as exc:
            actual_status = "error"
            policy_reason = f"benchmark_case_error: {type(exc).__name__}"
            error_message = str(exc)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        guard_expected_match = (
            None
            if case.expected_guard_allowed is None
            else guard_decision.allowed == case.expected_guard_allowed
        )
        execution_contract_match, execution_contract_reason = _evaluate_execution_contract_assertion(
            case,
            guard_decision,
        )
        routing_probe_match, routing_probe_actual = _evaluate_routing_probe(case)
        compaction_probe_match, compaction_probe_actual = _evaluate_compaction_probe(case)
        row_passed = actual_status == case.expected_status
        for probe_match in (
            execution_contract_match,
            routing_probe_match,
            compaction_probe_match,
        ):
            if probe_match is not None:
                row_passed = row_passed and probe_match
        row = {
            "name": case.name,
            "action": str(case.payload.get("action", "")),
            "expected_status": case.expected_status,
            "actual_status": actual_status,
            "passed": row_passed,
            "latency_ms": elapsed_ms,
            "category": case.category,
            "policy_reason": policy_reason,
            "runtime_guard_allowed": guard_decision.allowed,
            "runtime_guard_reason": guard_decision.reason,
            "runtime_guard_expected_match": guard_expected_match,
            "execution_contract_match": execution_contract_match,
            "execution_contract_reason": execution_contract_reason,
            "routing_probe_match": routing_probe_match,
            "routing_probe_actual": routing_probe_actual,
            "compaction_probe_match": compaction_probe_match,
            "compaction_probe_actual": compaction_probe_actual,
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
    guard_evaluations = [row for row in rows if isinstance(row.get("runtime_guard_allowed"), bool)]
    guard_allowed_count = sum(1 for row in guard_evaluations if bool(row.get("runtime_guard_allowed")))
    guard_expected_rows = [
        row for row in rows if isinstance(row.get("runtime_guard_expected_match"), bool)
    ]
    guard_expected_match_rate = (
        sum(1 for row in guard_expected_rows if bool(row.get("runtime_guard_expected_match")))
        / len(guard_expected_rows)
        if guard_expected_rows
        else 1.0
    )
    execution_contract_rows = [
        row for row in rows if isinstance(row.get("execution_contract_match"), bool)
    ]
    execution_contract_match_rate = (
        sum(1 for row in execution_contract_rows if bool(row.get("execution_contract_match")))
        / len(execution_contract_rows)
        if execution_contract_rows
        else 1.0
    )
    routing_probe_rows = [row for row in rows if isinstance(row.get("routing_probe_match"), bool)]
    routing_probe_match_rate = (
        sum(1 for row in routing_probe_rows if bool(row.get("routing_probe_match")))
        / len(routing_probe_rows)
        if routing_probe_rows
        else 1.0
    )
    compaction_probe_rows = [row for row in rows if isinstance(row.get("compaction_probe_match"), bool)]
    compaction_probe_match_rate = (
        sum(1 for row in compaction_probe_rows if bool(row.get("compaction_probe_match")))
        / len(compaction_probe_rows)
        if compaction_probe_rows
        else 1.0
    )

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
        "runtime_guard_allowed_rate": round(
            guard_allowed_count / len(guard_evaluations), 4
        )
        if guard_evaluations
        else 1.0,
        "runtime_guard_rejection_count": len(guard_evaluations) - guard_allowed_count,
        "runtime_guard_decision_match_rate": round(guard_expected_match_rate, 4),
        "execution_contract_match_rate": round(execution_contract_match_rate, 4),
        "routing_assertion_match_rate": round(routing_probe_match_rate, 4),
        "compaction_assertion_match_rate": round(compaction_probe_match_rate, 4),
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
    return {
        "metrics": metrics,
        "cases": rows,
        "probe_failures": _probe_failure_summary(rows),
    }


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
    parser.add_argument("--min-runtime-guard-match", type=float, default=0.9)
    parser.add_argument("--min-execution-contract-match", type=float, default=0.9)
    parser.add_argument("--min-routing-assertion-match", type=float, default=0.9)
    parser.add_argument("--min-compaction-assertion-match", type=float, default=0.9)
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
    min_runtime_guard_match: float,
    min_execution_contract_match: float,
    min_routing_assertion_match: float,
    min_compaction_assertion_match: float,
    required_categories: dict[str, int],
    category_rate_thresholds: dict[str, float],
    distinct_action_requirements: dict[str, int],
) -> dict[str, object]:
    tool_success = float(metrics.get("tool_success_rate", 0.0))
    refusal_quality = float(metrics.get("safety_refusal_quality", 0.0))
    error_rate = float(metrics.get("error_rate", 1.0))
    latency_p95 = float(metrics.get("latency_ms_p95", 0.0))
    runtime_guard_match = float(metrics.get("runtime_guard_decision_match_rate", 0.0))
    execution_contract_match = float(metrics.get("execution_contract_match_rate", 0.0))
    routing_assertion_match = float(metrics.get("routing_assertion_match_rate", 0.0))
    compaction_assertion_match = float(metrics.get("compaction_assertion_match_rate", 0.0))

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
        "runtime_guard_decision_match_rate": {
            "actual": round(runtime_guard_match, 4),
            "threshold": round(min_runtime_guard_match, 4),
            "comparator": ">=",
            "passed": runtime_guard_match >= min_runtime_guard_match,
        },
        "execution_contract_match_rate": {
            "actual": round(execution_contract_match, 4),
            "threshold": round(min_execution_contract_match, 4),
            "comparator": ">=",
            "passed": execution_contract_match >= min_execution_contract_match,
        },
        "routing_assertion_match_rate": {
            "actual": round(routing_assertion_match, 4),
            "threshold": round(min_routing_assertion_match, 4),
            "comparator": ">=",
            "passed": routing_assertion_match >= min_routing_assertion_match,
        },
        "compaction_assertion_match_rate": {
            "actual": round(compaction_assertion_match, 4),
            "threshold": round(min_compaction_assertion_match, 4),
            "comparator": ">=",
            "passed": compaction_assertion_match >= min_compaction_assertion_match,
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
        min_runtime_guard_match=args.min_runtime_guard_match,
        min_execution_contract_match=args.min_execution_contract_match,
        min_routing_assertion_match=args.min_routing_assertion_match,
        min_compaction_assertion_match=args.min_compaction_assertion_match,
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
