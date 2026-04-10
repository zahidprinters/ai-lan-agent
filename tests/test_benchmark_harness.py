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
    assert cli_payload["output"] == str(output_path)
