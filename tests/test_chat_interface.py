from __future__ import annotations

import json
import builtins
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from agents.react.controller import PlannedTurn
from runtime.chat_interface import (
    ChatSession,
    fallback_reply,
    format_router_result,
    parse_natural_action,
    run_chat_cli,
)
from runtime.perception_loop import PerceptionSnapshot
from tools.memory_store import add_memory_entry, get_recent_memories


def test_parse_natural_action_search() -> None:
    payload = parse_natural_action("search ai lan roadmap")
    assert payload is not None
    assert payload["action"] == "web.search"


def test_parse_natural_action_open_app_requires_medium_safety() -> None:
    payload = parse_natural_action("open app notepad")
    assert payload is not None
    assert payload["action"] == "pc.open_app"
    assert payload["safety_level"] == "medium"


def test_parse_natural_action_unknown_returns_none() -> None:
    assert parse_natural_action("tell me a joke") is None


def test_parse_natural_action_context_query() -> None:
    payload = parse_natural_action("context typing safety policy")
    assert payload is not None
    assert payload["action"] == "context.build"


def test_fallback_reply_for_greeting() -> None:
    assert "ready" in fallback_reply("hello").lower()


def test_format_router_result_includes_policy_reason() -> None:
    result = {
        "status": "rejected",
        "action": "pc.execute_shell",
        "policy_reason": "disabled",
        "observation": None,
    }
    text = format_router_result(result)
    assert "status: rejected" in text
    assert "policy: disabled" in text


def test_chat_session_confirm_flow(monkeypatch: Any) -> None:
    session = ChatSession()

    def fake_run(payload: dict[str, object], *, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            return {
                "status": "confirmation_required",
                "action": str(payload.get("action", "")),
                "policy_reason": "needs confirmation",
                "observation": None,
            }
        return {
            "status": "executed",
            "action": str(payload.get("action", "")),
            "policy_reason": "ok",
            "observation": True,
        }

    monkeypatch.setattr(session, "_run_payload", fake_run)

    first = session.handle_message("open app notepad")
    assert "confirmation_required" in first
    assert session.pending_payload is not None

    second = session.handle_message("/confirm")
    assert "status: executed" in second
    assert session.pending_payload is None


def test_chat_session_history_save_and_load(tmp_path: Path) -> None:
    session = ChatSession()
    session.handle_message("/help")
    session.handle_message("hello")

    assert len(session.turns) >= 4
    history_text = session.handle_message("/history")
    assert "user: /help" in history_text

    save_path = tmp_path / "chat_session.json"
    save_reply = session.handle_message(f"/save {save_path}")
    assert "Session saved" in save_reply
    assert save_path.exists()

    loaded = json.loads(save_path.read_text(encoding="utf-8"))
    assert "turns" in loaded

    new_session = ChatSession()
    load_reply = new_session.handle_message(f"/load {save_path}")
    assert "Session loaded" in load_reply
    assert len(new_session.turns) > 0


def test_chat_session_records_memory_and_context(tmp_path: Path, monkeypatch: Any) -> None:
    db_path = tmp_path / "memory.sqlite3"
    merged_path = tmp_path / "merged.txt"
    merged_path.write_text("docs are safe to list\n", encoding="utf-8")
    add_memory_entry(
        kind="notes",
        content="Docs are safe to list inside the workspace.",
        metadata={"topic": "docs"},
        db_path=db_path,
    )
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    session = ChatSession(memory_db_path=db_path, merged_corpus_path=merged_path)
    reply = session.handle_message("list docs")

    assert "status: executed" in reply
    assert session.last_context is not None
    assert session.last_context["query"] == "list docs"
    assert session.last_context["retrieval"]["memory_hits"]

    recent_memories = get_recent_memories(limit=5, db_path=db_path)
    assert any(entry.kind == "conversation" for entry in recent_memories)


def test_chat_session_uses_neural_controller_reply(monkeypatch: Any) -> None:
    session = ChatSession()
    monkeypatch.setattr(
        session, "_build_context", lambda text: {"query": text, "assembled_context": "context"}
    )
    monkeypatch.setattr(
        session.controller,
        "plan",
        lambda **kwargs: PlannedTurn(
            mode="reply",
            source="model",
            reply_text="I can help with that.",
            raw_text='{"mode":"reply"}',
        ),
    )

    reply = session.handle_message("please reason about the latest context")
    assert reply == "I can help with that."
    assert session.last_plan is not None
    assert session.last_plan["source"] == "model"


def test_chat_session_uses_neural_controller_action(monkeypatch: Any) -> None:
    session = ChatSession()
    monkeypatch.setattr(
        session, "_build_context", lambda text: {"query": text, "assembled_context": "context"}
    )
    monkeypatch.setattr(
        session.controller,
        "plan",
        lambda **kwargs: PlannedTurn(
            mode="action",
            source="model",
            action_payload={
                "thought": "Search memory for confirmation guidance.",
                "action": "memory.search",
                "args": {"query": "confirmation guidance"},
                "safety_level": "low",
            },
            raw_text='{"mode":"action"}',
        ),
    )

    def fake_run(payload: dict[str, object], *, confirmed: bool = False) -> dict[str, Any]:
        assert confirmed is False
        return {
            "status": "executed",
            "action": str(payload.get("action", "")),
            "policy_reason": "ok",
            "observation": {"hits": []},
        }

    monkeypatch.setattr(session, "_run_payload", fake_run)

    reply = session.handle_message("please inspect the latest guidance")
    assert "status: executed" in reply
    assert session.last_plan is not None
    assert session.last_plan["action"] == "memory.search"


def test_chat_session_runs_multi_step_neural_loop(monkeypatch: Any) -> None:
    session = ChatSession()
    monkeypatch.setattr(
        session, "_build_context", lambda text: {"query": text, "assembled_context": "context"}
    )

    def fake_plan(**kwargs: Any) -> PlannedTurn | None:
        observations = kwargs.get("recent_observations") or []
        if not observations:
            return PlannedTurn(
                mode="action",
                source="model",
                action_payload={
                    "thought": "Search memory for confirmation guidance.",
                    "action": "memory.search",
                    "args": {"query": "confirmation guidance"},
                    "safety_level": "low",
                },
                raw_text='{"mode":"action"}',
            )
        return PlannedTurn(
            mode="reply",
            source="model",
            reply_text="The latest guidance requires confirmation before typing.",
            raw_text='{"mode":"reply"}',
        )

    monkeypatch.setattr(session.controller, "plan", fake_plan)

    def fake_run(payload: dict[str, object], *, confirmed: bool = False) -> dict[str, Any]:
        assert confirmed is False
        return {
            "status": "executed",
            "action": str(payload.get("action", "")),
            "policy_reason": "ok",
            "observation": {"hits": [{"summary": "typing requires confirmation"}]},
        }

    monkeypatch.setattr(session, "_run_payload", fake_run)

    reply = session.handle_message("please inspect the latest guidance")
    assert reply == "The latest guidance requires confirmation before typing."
    assert session.last_plan is not None
    assert session.last_plan["mode"] == "reply"


def test_chat_session_recovers_after_reflection_retry(monkeypatch: Any) -> None:
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
            "observation": {"results": [{"title": "AI LAN roadmap"}]},
        }

    monkeypatch.setattr("agents.react.agent.parse_and_dispatch", fake_parse_and_dispatch)

    session = ChatSession()
    reply = session.handle_message("search ai lan roadmap")

    assert "status: executed" in reply
    assert len(calls) == 2
    assert calls[1]["args"] == {"query": "ai lan roadmap fallback"}


def test_chat_session_includes_perception_snapshot_in_context(monkeypatch: Any) -> None:
    session = ChatSession()
    session.perception_snapshot = PerceptionSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary="Outlook inbox visible with 14 unread messages.",
    )

    context = session._build_context("what is on screen")

    assert context["perception_summary"] == "Outlook inbox visible with 14 unread messages."
    assert "Perception Context:" in context["assembled_context"]


def test_chat_session_starts_perception_loop_when_enabled(monkeypatch: Any) -> None:
    started: list[int] = []
    stopped: list[int] = []

    class FakeLoop:
        def __init__(self, *, interval_sec: int, on_snapshot: Any) -> None:
            self.interval_sec = interval_sec
            self.on_snapshot = on_snapshot

        def start(self) -> None:
            started.append(self.interval_sec)
            self.on_snapshot(
                PerceptionSnapshot(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    summary="VS Code and inbox visible",
                )
            )

        def stop(self, timeout_sec: float = 2.0) -> None:
            _ = timeout_sec
            stopped.append(1)

    monkeypatch.setenv("AI_LAN_PERCEPTION_ENABLED", "1")
    monkeypatch.setenv("AI_LAN_PERCEPTION_INTERVAL_SEC", "7")
    monkeypatch.setattr("runtime.chat_interface.PerceptionLoop", FakeLoop)

    session = ChatSession()

    assert started == [7]
    assert session.perception_snapshot is not None
    assert session.perception_snapshot.summary == "VS Code and inbox visible"

    session.close()
    assert stopped == [1]


def test_chat_session_save_and_load_preserves_perception_snapshot(tmp_path: Path) -> None:
    session = ChatSession()
    session.perception_snapshot = PerceptionSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary="Build failed window visible",
    )

    save_path = tmp_path / "session_with_perception.json"
    session.save_session(str(save_path))

    loaded = ChatSession()
    loaded.load_session(str(save_path))

    assert loaded.perception_snapshot is not None
    assert loaded.perception_snapshot.summary == "Build failed window visible"


def test_run_chat_cli_closes_session_on_exit(monkeypatch: Any) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def handle_message(self, message: str) -> str:
            return f"echo:{message}"

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()
    inputs = iter(["/quit"])

    monkeypatch.setattr("runtime.chat_interface.ChatSession", lambda: fake_session)
    monkeypatch.setattr(builtins, "input", lambda _='': next(inputs))

    code = run_chat_cli()

    assert code == 0
    assert fake_session.closed is True
