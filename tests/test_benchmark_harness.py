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
    assert cli_payload["metrics"]["tool_success_rate"] >= 0.0
    assert "gate" in report
    assert "passed" in report["gate"]


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
