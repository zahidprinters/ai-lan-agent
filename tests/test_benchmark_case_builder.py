from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_benchmark_cases_from_audit import build_cases_from_audit, write_cases


@pytest.mark.unit
def test_build_cases_from_audit_deduplicates_and_maps_statuses(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    rows = [
        {
            "timestamp": "2026-04-11T00:00:00+00:00",
            "request": {
                "thought": "Search docs",
                "action": "memory.search",
                "args": {"query": "policy"},
                "safety_level": "low",
            },
            "result": {
                "status": "executed",
                "action": "memory.search",
                "observation": [],
                "policy_reason": "allowed",
            },
        },
        {
            "timestamp": "2026-04-11T00:00:01+00:00",
            "request": {
                "thought": "Search docs again",
                "action": "memory.search",
                "args": {"query": "policy"},
                "safety_level": "low",
            },
            "result": {
                "status": "executed",
                "action": "memory.search",
                "observation": [],
                "policy_reason": "allowed",
            },
        },
        {
            "timestamp": "2026-04-11T00:00:02+00:00",
            "request": {
                "thought": "Type text",
                "action": "pc.type_text",
                "args": {"text": "hello"},
                "safety_level": "medium",
            },
            "result": {
                "status": "confirmation_required",
                "action": "pc.type_text",
                "observation": None,
                "policy_reason": "confirm",
            },
        },
        {
            "timestamp": "2026-04-11T00:00:03+00:00",
            "request": {
                "thought": "Run shell",
                "action": "pc.execute_shell",
                "args": {"command": "dir"},
                "safety_level": "high",
            },
            "result": {
                "status": "rejected",
                "action": "pc.execute_shell",
                "observation": None,
                "policy_reason": "disabled",
            },
        },
    ]
    audit_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    cases = build_cases_from_audit(audit_path)

    assert len(cases) == 3
    assert cases[0].expected_status == "executed"
    assert cases[0].confirmed is True
    assert cases[0].category == "execution"
    assert cases[1].expected_status == "confirmation_required"
    assert cases[1].confirmed is False
    assert cases[1].category == "confirmation"
    assert cases[2].expected_status == "rejected"
    assert cases[2].category == "refusal"


@pytest.mark.unit
def test_build_cases_from_audit_respects_max_cases_and_write_output(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    output_path = tmp_path / "cases.json"
    rows = [
        {
            "timestamp": "2026-04-11T00:00:00+00:00",
            "request": {
                "thought": f"req-{index}",
                "action": "memory.search",
                "args": {"query": f"policy-{index}"},
                "safety_level": "low",
            },
            "result": {
                "status": "executed",
                "action": "memory.search",
                "observation": [],
                "policy_reason": "allowed",
            },
        }
        for index in range(5)
    ]
    audit_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    cases = build_cases_from_audit(audit_path, max_cases=2)
    write_cases(output_path, cases)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(cases) == 2
    assert len(payload) == 2
    assert payload[0]["confirmed"] is True
    assert payload[0]["expected_status"] == "executed"