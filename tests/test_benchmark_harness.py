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
