from __future__ import annotations

import importlib
from pathlib import Path
import pytest

from agents.react.agent import ReactAgent, run_react_step
from memory.short_term.buffer import ShortTermBuffer
from router.router import parse_and_dispatch
from runtime.context import build_runtime_context
from safety.policy_engine import evaluate_policy, should_require_confirmation
from tools.memory_store import add_memory_entry
from tools.web.search import WebSearchTool


@pytest.fixture(autouse=True)
def _reset_policy_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(root / "config" / "policies.yaml"))
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(root / "config" / "settings.yaml"))

    import safety.policy_engine as pe

    importlib.reload(pe)


def test_short_term_buffer_role_and_context_text() -> None:
    buffer = ShortTermBuffer(max_items=3)
    buffer.add(role="user", message="hello")
    buffer.add(role="assistant", message="hi")

    items = buffer.get_all()
    assert len(items) == 2
    assert items[0].role == "user"
    assert "assistant: hi" in buffer.to_context_text()


def test_policy_engine_accepts_raw_payload() -> None:
    decision = evaluate_policy(
        {
            "thought": "type message",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        }
    )

    assert decision.allowed is True
    assert should_require_confirmation(
        {
            "thought": "type message",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        }
    )


def test_router_parse_and_dispatch_executes_low_risk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    result = parse_and_dispatch(
        {
            "thought": "list docs",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 3},
            "safety_level": "low",
        }
    )

    assert result["status"] == "executed"
    assert result["action"] == "pc.list_workspace_files"


def test_router_dispatch_executes_memory_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Fallback route should still execute memory search.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    result = parse_and_dispatch(
        {
            "thought": "search stored memory",
            "action": "memory.search",
            "args": {"query": "fallback memory", "db_path": str(db_path)},
            "safety_level": "low",
        }
    )

    assert result["status"] == "executed"
    assert result["action"] == "memory.search"


def test_react_agent_tracks_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    agent = ReactAgent()

    step = agent.run_step(
        {
            "thought": "list docs",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 3},
            "safety_level": "low",
        }
    )

    assert step.result["status"] == "executed"
    assert agent.state.thoughts
    assert agent.state.observations
    assert step.result["action"] == "pc.list_workspace_files"


def test_react_agent_reflection_retries_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_REFLECTION_RETRIES", "1")
    monkeypatch.setenv("AI_LAN_REFLECTION_RETRIES_PER_TURN", "3")

    calls: list[dict[str, object]] = []

    def fake_parse_and_dispatch(
        payload: dict[str, object], *, confirmed: bool = False, **_: object
    ) -> dict[str, object]:
        assert confirmed is False
        calls.append(payload)
        if len(calls) == 1:
            return {
                "status": "failed",
                "action": "web.search",
                "policy_reason": "timeout",
                "observation": None,
            }
        return {
            "status": "executed",
            "action": "web.search",
            "policy_reason": "ok",
            "observation": {"results": [{"title": "AI LAN"}]},
        }

    monkeypatch.setattr("agents.react.agent.parse_and_dispatch", fake_parse_and_dispatch)

    agent = ReactAgent()
    step = agent.run_step(
        {
            "thought": "search roadmap",
            "action": "web.search",
            "args": {"query": "ai lan roadmap"},
            "safety_level": "low",
        }
    )

    assert len(calls) == 2
    assert calls[1]["args"] == {"query": "ai lan roadmap fallback"}
    assert step.result["status"] == "executed"
    assert step.result["reflection_retry_count"] == 1
    assert step.result["reflection_applied"] is True
    assert step.result["reflection_notes"]


def test_react_agent_reflection_budget_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_REFLECTION_RETRIES", "1")
    monkeypatch.setenv("AI_LAN_REFLECTION_RETRIES_PER_TURN", "3")

    calls = {"count": 0}

    def fake_parse_and_dispatch(
        payload: dict[str, object], *, confirmed: bool = False, **_: object
    ) -> dict[str, object]:
        _ = payload
        assert confirmed is False
        calls["count"] += 1
        return {
            "status": "failed",
            "action": "web.search",
            "policy_reason": "timeout",
            "observation": None,
        }

    monkeypatch.setattr("agents.react.agent.parse_and_dispatch", fake_parse_and_dispatch)

    agent = ReactAgent()
    payload = {
        "thought": "search roadmap",
        "action": "web.search",
        "args": {"query": "ai lan roadmap"},
        "safety_level": "low",
    }
    for _ in range(3):
        step = agent.run_step(payload)
        assert step.result["reflection_retry_count"] == 1

    final_step = agent.run_step(payload)

    assert calls["count"] == 7
    assert final_step.result["reflection_retry_count"] == 0
    assert final_step.result["reflection_skipped_reason"] == "retry_budget_exhausted"
    assert agent.state.reflection_retries_used == 3


def test_react_agent_writes_structured_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_AGENT_LOG_PATH", str(tmp_path / "agent.jsonl"))
    monkeypatch.setenv("AI_LAN_TOOL_LOG_PATH", str(tmp_path / "tool.jsonl"))
    monkeypatch.setenv("AI_LAN_ERROR_LOG_PATH", str(tmp_path / "error.jsonl"))

    monkeypatch.setattr(
        "agents.react.agent.parse_and_dispatch",
        lambda payload, **_: {
            "status": "executed",
            "action": str(payload.get("action", "")),
            "policy_reason": "ok",
            "observation": {"hits": []},
        },
    )

    agent = ReactAgent()
    agent.run_step(
        {
            "thought": "list docs",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 2},
            "safety_level": "low",
        }
    )

    assert (tmp_path / "agent.jsonl").exists()
    assert (tmp_path / "tool.jsonl").exists()
    assert not (tmp_path / "error.jsonl").exists()
    assert 'risk_profile' in (tmp_path / 'tool.jsonl').read_text(encoding='utf-8')


def test_run_react_step_stateless_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    result = run_react_step(
        {
            "thought": "list docs",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 2},
            "safety_level": "low",
        }
    )

    assert "request" in result
    assert result["result"]["status"] == "executed"


def test_runtime_context_includes_short_term_and_retrieval(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    merged = tmp_path / "merged.txt"
    merged.write_text("safe typing needs confirmation\n", encoding="utf-8")

    add_memory_entry(
        kind="notes",
        content="Typing actions require confirmation under policy.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    short_term = ShortTermBuffer()
    short_term.add(role="user", message="how do we keep typing safe")

    context = build_runtime_context(
        query="typing confirmation policy",
        short_term_buffer=short_term,
        memory_db_path=db_path,
        merged_corpus_path=merged,
    )

    assert "Short-Term Context:" in context["assembled_context"]
    assert "Retrieved Context:" in context["assembled_context"]


def test_web_search_tool_requires_query() -> None:
    tool = WebSearchTool()
    try:
        tool.run()
        raised = False
    except ValueError:
        raised = True
    assert raised is True


def test_runtime_context_truncates_sections_for_low_resource_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    merged = tmp_path / "merged.txt"
    merged.write_text("typing confirmation policy guidance\n", encoding="utf-8")

    add_memory_entry(
        kind="notes",
        content="Typing actions require confirmation under policy.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    short_term = ShortTermBuffer()
    short_term.add(role="user", message="x" * 500)

    context = build_runtime_context(
        query="typing confirmation policy",
        short_term_buffer=short_term,
        memory_db_path=db_path,
        merged_corpus_path=merged,
        max_context_chars=120,
    )

    assert context["short_term_context"].startswith("...")
    assert "Perception Context:" in context["assembled_context"]
