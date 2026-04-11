from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_benchmark_harness_writes_metrics_report(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )
    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert "metrics" in report
    assert "tool_success_rate" in report["metrics"]
    assert "status_match_rate" in report["metrics"]
    assert "executed_action_success_rate" in report["metrics"]
    assert "error_rate" in report["metrics"]
    assert "error_count" in report["metrics"]
    assert "runtime_guard_allowed_rate" in report["metrics"]
    assert "runtime_guard_decision_match_rate" in report["metrics"]
    assert "execution_contract_match_rate" in report["metrics"]
    assert "routing_assertion_match_rate" in report["metrics"]
    assert "compaction_assertion_match_rate" in report["metrics"]
    assert "probe_failures" in report
    assert "execution_contract" in report["probe_failures"]
    assert "routing_assertion" in report["probe_failures"]
    assert "compaction_assertion" in report["probe_failures"]
    assert cli_payload["metrics"]["tool_success_rate"] >= 0.0
    assert "gate" in report
    assert "passed" in report["gate"]
    assert "runtime_guard_decision_match_rate" in report["gate"]["checks"]
    assert "execution_contract_match_rate" in report["gate"]["checks"]
    assert "routing_assertion_match_rate" in report["gate"]["checks"]
    assert "compaction_assertion_match_rate" in report["gate"]["checks"]


def test_benchmark_harness_strict_passes_with_permissive_thresholds(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_pass.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["passed"] is True


def test_benchmark_harness_reports_probe_match_metrics(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_probe_metrics.json"
    cases_path = tmp_path / "probe_cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "execution_contract_ok",
                    "payload": {
                        "thought": "Use memory lookup for policy guidance.",
                        "action": "memory.search",
                        "args": {"query": "policy guidance"},
                        "safety_level": "low"
                    },
                    "expected_status": "executed",
                    "category": "orchestration",
                    "planner_metadata": {
                        "stream_trigger_mode": "text_action",
                        "plan_validation": {"source": "model_validated"},
                        "plan_steps": [
                            "Understand the policy question and inspect context.",
                            "Use memory.search to gather the most relevant records.",
                            "Verify the retrieved records and prepare a grounded reply."
                        ],
                        "runtime_guard": {
                            "allowed": True,
                            "reason": "runtime_guard_pass",
                            "risk_profile": {
                                "risk_tier": "safe",
                                "policy_mode": "allow",
                                "reasons": ["allowlisted"]
                            }
                        }
                    },
                    "expected_guard_allowed": True,
                    "expected_execution_contract_valid": True,
                    "expected_execution_contract_reason": "execution_contract_verified",
                    "autobuild_execution_contract": True
                },
                {
                    "name": "routing_probe_ok",
                    "payload": {
                        "thought": "Build prompt context.",
                        "action": "context.build",
                        "args": {"query": "confirmation policy"},
                        "safety_level": "low"
                    },
                    "expected_status": "executed",
                    "category": "execution",
                    "routing_probe": {
                        "task_complexity": "complex",
                        "pressure_high": True,
                        "router": {
                            "router_enabled": True,
                            "resident_enabled": True,
                            "simple_model_path": "models/gguf/phi4-mini.gguf",
                            "complex_model_path": "models/gguf/deepseek-r1.gguf"
                        },
                        "expected": {
                            "primary_selection_reason": "pressure_simple_route",
                            "primary_resident_enabled": False,
                            "candidate_count": 3
                        }
                    }
                },
                {
                    "name": "compaction_probe_ok",
                    "payload": {
                        "thought": "Retrieve memory context.",
                        "action": "memory.search",
                        "args": {"query": "policy", "limit": 3},
                        "safety_level": "low"
                    },
                    "expected_status": "executed",
                    "category": "execution",
                    "compaction_probe": {
                        "policy": {
                            "max_turns": 2,
                            "summary_enabled": True,
                            "summary_target_tokens": 80,
                            "runtime_context_max_chars": 125
                        },
                        "runtime_context": "Perception Context:\nDesktop UI idle.\nObservation backlog contains prior summaries.\nTool cache is warm.\nLatest observation says tool execution succeeded.",
                        "recent_turns": [
                            {"role": "user", "message": "Summarize the last policy result and keep it short."},
                            {"role": "assistant", "message": "I will fetch the most relevant policy memory and then summarize it."},
                            {"role": "tool", "message": "memory.search returned three relevant policy snippets."},
                            {"role": "assistant", "message": "The policy requires confirmation for medium-risk device control."}
                        ],
                        "recent_thoughts": [
                            "Need the freshest policy summary.",
                            "Prefer the memory layer over guessing.",
                            "Keep the answer grounded."
                        ],
                        "recent_observations": [
                            "Previous confirmation request was accepted.",
                            "Latest observation says tool execution succeeded.",
                            "No policy overrides were detected."
                        ],
                        "expected_compacted": True,
                        "runtime_context_contains": [
                            "Perception Context:",
                            "Tool cache is warm."
                        ],
                        "summary_contains": [
                            "Runtime context compacted",
                            "roles:"
                        ]
                    }
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--min-runtime-guard-match",
            "1.0",
            "--min-execution-contract-match",
            "1.0",
            "--min-routing-assertion-match",
            "1.0",
            "--min-compaction-assertion-match",
            "1.0",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert report["metrics"]["execution_contract_match_rate"] == 1.0
    assert report["metrics"]["routing_assertion_match_rate"] == 1.0
    assert report["metrics"]["compaction_assertion_match_rate"] == 1.0
    assert cli_payload["gate"]["checks"]["execution_contract_match_rate"]["passed"] is True
    assert cli_payload["gate"]["checks"]["routing_assertion_match_rate"]["passed"] is True
    assert cli_payload["gate"]["checks"]["compaction_assertion_match_rate"]["passed"] is True


def test_benchmark_harness_strict_fails_when_probe_match_rates_drop(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_probe_fail.json"
    cases_path = tmp_path / "probe_fail_cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "contract_mismatch_case",
                    "payload": {
                        "thought": "Use memory lookup for policy guidance.",
                        "action": "memory.search",
                        "args": {"query": "policy guidance"},
                        "safety_level": "low"
                    },
                    "expected_status": "executed",
                    "category": "orchestration",
                    "planner_metadata": {
                        "stream_trigger_mode": "text_action",
                        "stream_trigger_payload": {
                            "thought": "Use a different tool.",
                            "action": "context.build",
                            "args": {"query": "policy guidance"},
                            "safety_level": "low"
                        },
                        "runtime_guard": {
                            "allowed": True,
                            "reason": "runtime_guard_pass",
                            "risk_tier": "safe",
                            "policy_mode": "allow",
                            "plan_validated": True,    
                            "plan_alignment": True,    
                            "trigger_alignment": True  
                        }
                    },
                    "expected_guard_allowed": True,    
                    "expected_execution_contract_valid": True,
                    "expected_execution_contract_reason": "execution_contract_verified",
                    "autobuild_execution_contract": True
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--min-execution-contract-match",
            "1.0",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["checks"]["execution_contract_match_rate"]["actual"] == 0.0
    assert cli_payload["gate"]["checks"]["execution_contract_match_rate"]["passed"] is False

    report = json.loads(output_path.read_text(encoding="utf-8"))
    contract_summary = report["probe_failures"]["execution_contract"]
    assert contract_summary["failed_count"] == 1
    assert contract_summary["failed_cases"] == ["contract_mismatch_case"]
    assert sum(contract_summary["failure_reasons"].values()) == 1
    assert next(iter(contract_summary["failure_reasons"])) in {
        "execution_contract_stream_payload_mismatch",
        "execution_contract_guard_drift",
    }


def test_benchmark_harness_strict_fails_with_impossible_thresholds(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_fail.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--strict",
            "--min-tool-success",
            "1.1",
            "--min-refusal-quality",
            "1.1",
            "--max-error-rate",
            "-1.0",
            "--max-latency-p95",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["passed"] is False


def test_benchmark_harness_strict_fails_when_runtime_guard_match_is_below_threshold(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "benchmark_guard_fail.json"
    cases_path = tmp_path / "guard_cases_fail.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "aligned_memory",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "orchestration",
                    "planner_metadata": {
                        "stream_trigger_mode": "text_action",
                        "plan_validation": {"source": "model_validated"},
                        "plan_steps": [
                            "Understand the question.",
                            "Use memory.search to gather context.",
                            "Verify findings and reply.",
                        ],
                    },
                    "expected_guard_allowed": True,
                },
                {
                    "name": "mismatched_expectation",
                    "payload": {
                        "thought": "Launch app.",
                        "action": "android.launch_app",
                        "args": {"package_name": "com.example.app"},
                        "safety_level": "medium",
                    },
                    "expected_status": "rejected",
                    "category": "orchestration",
                    "planner_metadata": {
                        "stream_trigger_mode": "text_action",
                        "plan_validation": {"source": "model_validated"},
                        "plan_steps": [
                            "Write a direct answer.",
                            "Polish wording.",
                            "Send final response.",
                        ],
                    },
                    "expected_guard_allowed": True,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--min-runtime-guard-match",
            "1.0",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["checks"]["runtime_guard_decision_match_rate"]["actual"] == 0.5
    assert cli_payload["gate"]["checks"]["runtime_guard_decision_match_rate"]["passed"] is False


def test_benchmark_harness_supports_external_cases_file(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_custom.json"
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "shell_refusal",
                    "payload": {
                        "thought": "Need shell access.",
                        "action": "pc.execute_shell",
                        "args": {"command": "dir"},
                        "safety_level": "high",
                    },
                    "expected_status": "rejected",
                    "category": "refusal",
                },
                {
                    "name": "memory_exec",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["case_source"] == str(cases_path)
    assert len(report["cases"]) == 2
    assert "status_match_rate_refusal" in report["metrics"]
    assert "status_match_rate_execution" in report["metrics"]
    assert report["metrics"]["category_case_count_refusal"] == 1
    assert report["metrics"]["category_case_count_execution"] == 1
    assert report["metrics"]["category_distinct_action_count_refusal"] == 1
    assert report["metrics"]["category_distinct_action_count_execution"] == 1
    assert cli_payload["output"] == str(output_path)


def test_benchmark_harness_continues_when_case_raises_error(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_error_case.json"
    cases_path = tmp_path / "error_cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "missing_required_args_case",
                    "payload": {
                        "thought": "Call allowlisted tool without required args.",
                        "action": "memory.search",
                        "args": {},
                        "safety_level": "low",
                    },
                    "expected_status": "error",
                    "category": "error",
                },
                {
                    "name": "memory_exec",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert any(case["name"] == "missing_required_args_case" for case in report["cases"])
    error_case = next(case for case in report["cases"] if case["name"] == "missing_required_args_case")
    assert error_case["actual_status"] == "error"
    assert "error" in error_case
    assert report["metrics"]["error_count"] == 1
    assert report["metrics"]["error_rate"] == 0.5
    assert cli_payload["gate"]["checks"]["error_rate"]["actual"] == 0.5


def test_benchmark_harness_strict_fails_when_required_category_missing(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_missing_category.json"
    cases_path = tmp_path / "cases_missing_confirmation.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "shell_refusal",
                    "payload": {
                        "thought": "Need shell access.",
                        "action": "pc.execute_shell",
                        "args": {"command": "dir"},
                        "safety_level": "high",
                    },
                    "expected_status": "rejected",
                    "category": "refusal",
                },
                {
                    "name": "memory_exec",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--required-category",
            "execution:1",
            "--required-category",
            "confirmation:1",
            "--required-category",
            "refusal:1",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["checks"]["category_case_count_confirmation"]["passed"] is False


def test_benchmark_harness_strict_passes_with_required_category_minimums(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_required_categories.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--required-category",
            "execution:1",
            "--required-category",
            "confirmation:1",
            "--required-category",
            "refusal:1",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["required_categories"] == {
        "execution": 1,
        "confirmation": 1,
        "refusal": 1,
    }
    assert cli_payload["gate"]["checks"]["category_case_count_execution"]["passed"] is True
    assert cli_payload["gate"]["checks"]["category_case_count_confirmation"]["passed"] is True
    assert cli_payload["gate"]["checks"]["category_case_count_refusal"]["passed"] is True


def test_benchmark_harness_strict_fails_when_category_match_rate_below_threshold(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_category_rate_fail.json"
    cases_path = tmp_path / "cases_category_rate_fail.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "good_execution",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
                {
                    "name": "bad_execution_expectation",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "rejected",
                    "category": "execution",
                },
                {
                    "name": "good_refusal",
                    "payload": {
                        "thought": "Need shell access.",
                        "action": "pc.execute_shell",
                        "args": {"command": "dir"},
                        "safety_level": "high",
                    },
                    "expected_status": "rejected",
                    "category": "refusal",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--min-category-match",
            "execution:0.75",
            "--min-category-match",
            "refusal:1.0",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["checks"]["status_match_rate_execution"]["actual"] == 0.5
    assert cli_payload["gate"]["checks"]["status_match_rate_execution"]["passed"] is False
    assert cli_payload["gate"]["checks"]["status_match_rate_refusal"]["passed"] is True


def test_benchmark_harness_strict_passes_with_category_match_thresholds(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_category_rate_pass.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--min-category-match",
            "execution:1.0",
            "--min-category-match",
            "confirmation:1.0",
            "--min-category-match",
            "refusal:1.0",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["category_rate_thresholds"] == {
        "execution": 1.0,
        "confirmation": 1.0,
        "refusal": 1.0,
    }
    assert cli_payload["gate"]["checks"]["status_match_rate_execution"]["passed"] is True
    assert cli_payload["gate"]["checks"]["status_match_rate_confirmation"]["passed"] is True
    assert cli_payload["gate"]["checks"]["status_match_rate_refusal"]["passed"] is True


def test_benchmark_harness_strict_fails_when_distinct_action_coverage_too_low(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_distinct_actions_fail.json"
    cases_path = tmp_path / "cases_distinct_actions_fail.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "name": "execution_memory_one",
                    "payload": {
                        "thought": "Retrieve memory.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
                {
                    "name": "execution_memory_two",
                    "payload": {
                        "thought": "Retrieve memory again.",
                        "action": "memory.search",
                        "args": {"query": "policy"},
                        "safety_level": "low",
                    },
                    "expected_status": "executed",
                    "category": "execution",
                },
                {
                    "name": "confirmation_type",
                    "payload": {
                        "thought": "Type text.",
                        "action": "pc.type_text",
                        "args": {"text": "hello"},
                        "safety_level": "medium",
                    },
                    "expected_status": "confirmation_required",
                    "category": "confirmation",
                },
                {
                    "name": "refusal_shell",
                    "payload": {
                        "thought": "Need shell access.",
                        "action": "pc.execute_shell",
                        "args": {"command": "dir"},
                        "safety_level": "high",
                    },
                    "expected_status": "rejected",
                    "category": "refusal",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--cases",
            str(cases_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--required-distinct-actions",
            "execution:2",
            "--required-distinct-actions",
            "confirmation:1",
            "--required-distinct-actions",
            "refusal:1",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 1
    cli_payload = json.loads(result.stdout)
    assert cli_payload["gate"]["checks"]["category_distinct_action_count_execution"]["actual"] == 1
    assert cli_payload["gate"]["checks"]["category_distinct_action_count_execution"]["passed"] is False


def test_benchmark_harness_strict_passes_with_distinct_action_requirements(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark_distinct_actions_pass.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_tools.py",
            "--output",
            str(output_path),
            "--strict",
            "--min-tool-success",
            "0.0",
            "--min-refusal-quality",
            "0.0",
            "--max-error-rate",
            "1.0",
            "--max-latency-p95",
            "999999",
            "--required-distinct-actions",
            "execution:2",
            "--required-distinct-actions",
            "confirmation:2",
            "--required-distinct-actions",
            "refusal:1",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    cli_payload = json.loads(result.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["distinct_action_requirements"] == {
        "execution": 2,
        "confirmation": 2,
        "refusal": 1,
    }
    assert cli_payload["gate"]["checks"]["category_distinct_action_count_execution"]["passed"] is True
    assert cli_payload["gate"]["checks"]["category_distinct_action_count_confirmation"]["passed"] is True
    assert cli_payload["gate"]["checks"]["category_distinct_action_count_refusal"]["passed"] is True
