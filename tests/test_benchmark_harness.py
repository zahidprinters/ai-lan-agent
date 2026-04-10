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
