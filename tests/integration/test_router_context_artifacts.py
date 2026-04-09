from __future__ import annotations

from pathlib import Path

import pytest

from router.dispatch_core import dispatch_agent_action
from tools.memory_store import add_memory_entry


@pytest.mark.integration
def test_router_context_builder_uses_persisted_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    memory_db = tmp_path / "memory.sqlite3"
    merged_corpus = tmp_path / "merged.txt"
    merged_corpus.write_text(
        "policy confirms write actions\n" "retrieval context includes memory and snippets\n",
        encoding="utf-8",
    )
    add_memory_entry(
        kind="notes",
        content="Write actions must be confirmed by policy.",
        db_path=memory_db,
    )

    memory_result = dispatch_agent_action(
        {
            "thought": "Find policy memory",
            "action": "memory.search",
            "args": {"query": "confirmed write actions", "db_path": str(memory_db)},
            "safety_level": "low",
        }
    )
    context_result = dispatch_agent_action(
        {
            "thought": "Build full context",
            "action": "context.build",
            "args": {
                "query": "policy write actions",
                "db_path": str(memory_db),
                "merged_corpus_path": str(merged_corpus),
            },
            "safety_level": "low",
        }
    )

    assert memory_result.status == "executed"
    assert context_result.status == "executed"
    assert context_result.observation["memory_hits"]
    assert context_result.observation["corpus_snippets"]
