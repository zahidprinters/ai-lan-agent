from __future__ import annotations

import json
from pathlib import Path

import pytest

from router.dispatch_core import ToolSpec, dispatch_agent_action
from scripts.replay_audit import replay_audit_log


@pytest.mark.unit
def test_dispatch_dry_run_skips_handler_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    calls = {"count": 0}

    def fake_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
        calls["count"] += 1
        return [{"Title": query, "Snippet": "ok", "URL": "local"}]

    from router import dispatch_core as router_core

    monkeypatch.setitem(
        router_core.TOOL_REGISTRY,
        "web.search",
        ToolSpec(fake_search, ("query",), ("max_results",)),
    )

    result = dispatch_agent_action(
        {
            "thought": "search",
            "action": "web.search",
            "args": {"query": "AI Lan"},
            "safety_level": "low",
        },
        dry_run=True,
    )

    assert result.status == "dry_run"
    assert calls["count"] == 0


@pytest.mark.unit
def test_dispatch_dry_run_respects_confirmation_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    pending = dispatch_agent_action(
        {
            "thought": "type",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        },
        dry_run=True,
        confirmed=False,
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "type",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        },
        dry_run=True,
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "dry_run"


@pytest.mark.unit
def test_replay_audit_log_reports_decision_matches(tmp_path: Path) -> None:
    audit_file = tmp_path / "action_audit.jsonl"
    rows = [
        {
            "timestamp": "2026-04-10T00:00:00+00:00",
            "request": {
                "thought": "Search docs",
                "action": "web.search",
                "args": {"query": "AI Lan"},
                "safety_level": "low",
            },
            "result": {
                "status": "executed",
                "action": "web.search",
                "observation": [],
                "policy_reason": "allowed",
            },
        },
        {
            "timestamp": "2026-04-10T00:00:01+00:00",
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
    audit_file.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    report = replay_audit_log(audit_file)

    assert report["total_rows"] == 2
    assert report["parse_errors"] == 0
    assert report["decision_match_rate"] == 1.0
