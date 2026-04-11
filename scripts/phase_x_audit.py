from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GateResult:
    name: str
    command: str
    exit_code: int
    passed: bool
    duration_sec: float
    output_tail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "exit_code": self.exit_code,
            "passed": self.passed,
            "duration_sec": round(self.duration_sec, 3),
            "output_tail": self.output_tail,
        }


def _run_gate(name: str, command: str) -> GateResult:
    start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    end = time.monotonic()
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    lines = [line for line in output.splitlines() if line.strip()]
    output_tail = "\n".join(lines[-12:])
    return GateResult(
        name=name,
        command=command,
        exit_code=completed.returncode,
        passed=completed.returncode == 0,
        duration_sec=end - start,
        output_tail=output_tail,
    )


def _phase_summary(gates: dict[str, GateResult]) -> dict[str, dict[str, Any]]:
    x0_pass = gates["unit"].passed and gates["replay"].passed
    x1_pass = gates["reasoning"].passed and gates["benchmark"].passed
    x2_pass = gates["safety"].passed and gates["replay"].passed

    return {
        "X0": {
            "status": "pass" if x0_pass else "fail",
            "required_gates": ["unit", "replay"],
        },
        "X1": {
            "status": "pass" if x1_pass else "fail",
            "required_gates": ["reasoning", "benchmark"],
        },
        "X2": {
            "status": "pass" if x2_pass else "fail",
            "required_gates": ["safety", "replay"],
        },
        "X3": {
            "status": "manual",
            "note": "Embodied-lite checks remain manual/hardware-session scoped.",
        },
        "X4": {
            "status": "in_progress",
            "note": "Readiness lane; use this report as one reproducible readiness artifact.",
        },
        "X5": {
            "status": "deferred",
            "note": "Heavy-machine execution lane.",
        },
        "X6": {
            "status": "deferred",
            "note": "Heavy-machine promotion/ops lane.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase X gate audit for the current machine.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "phase_x_audit_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when any mandatory gate in X0-X2 fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    gate_commands = {
        "unit": "python -m pytest tests -m unit -q --disable-warnings",
        "safety": "python -m pytest tests/test_dynamic_safety.py tests/test_policy_engine_config.py -q --disable-warnings",
        "reasoning": "python -m pytest tests/test_local_reasoning.py tests/test_chat_interface.py tests/test_layered_modules.py -q --disable-warnings",
        "replay": "python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict",
        "benchmark": "python scripts/benchmark_tools.py --output temp/benchmarks/local_tool_benchmark.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-latency-p95 2500",
    }

    gates: dict[str, GateResult] = {}
    for gate_name, command in gate_commands.items():
        gates[gate_name] = _run_gate(gate_name, command)

    phase = _phase_summary(gates)
    strict_failed = any(phase[key]["status"] == "fail" for key in ("X0", "X1", "X2"))

    report = {
        "machine": "i5_16gb_cpu_first",
        "phase": phase,
        "gates": {name: result.to_dict() for name, result in gates.items()},
        "strict": args.strict,
        "strict_failed": bool(args.strict and strict_failed),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(args.output),
                "strict": args.strict,
                "strict_failed": bool(args.strict and strict_failed),
                "phase": {k: v["status"] for k, v in phase.items()},
            },
            indent=2,
        )
    )

    if args.strict and strict_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
