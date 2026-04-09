from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.memory_store import (
    add_memory_entry,
    get_recent_memories,
    retrieve_relevant_memories,
    store_conversation_summary,
)


def test_store_and_retrieve_memory_entries(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Router policy should require confirmation for typing actions.",
        metadata={"phase": 4},
        db_path=db_path,
    )
    add_memory_entry(
        kind="notes",
        content="Ingestion pipeline merges trusted sources and removes duplicates.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    hits = retrieve_relevant_memories(query="typing confirmation policy", db_path=db_path)
    assert hits
    assert hits[0].kind == "notes"
    assert "typing actions" in hits[0].summary.lower()


def test_semantic_memory_retrieval_prefers_related_entry(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Typing actions require confirmation before execution.",
        metadata={"phase": 4},
        db_path=db_path,
    )
    add_memory_entry(
        kind="notes",
        content="The garden hose is green.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    hits = retrieve_relevant_memories(query="approval to enter text", db_path=db_path)
    assert hits
    assert "confirmation" in hits[0].summary.lower() or "typing" in hits[0].summary.lower()


def test_store_conversation_summary_and_recent_listing(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    entry = store_conversation_summary(
        user_text="Please set up memory retrieval next.",
        assistant_text="I added a SQLite memory store and retrieval API.",
        metadata={"ticket": "phase4-memory"},
        db_path=db_path,
    )

    assert entry.kind == "conversation"
    recent = get_recent_memories(db_path=db_path)
    assert len(recent) == 1
    assert recent[0].metadata["ticket"] == "phase4-memory"


def test_memory_store_cli_search(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    env = {
        **dict(),
    }
    env.update(
        {
            "AI_LAN_DEBUG": "0",
            "AI_LAN_TRACE": "0",
            "AI_LAN_PROFILE": "0",
        }
    )
    # Preserve current process environment while forcing deterministic quiet output.
    import os

    env = {**os.environ, **env}
    subprocess.run(
        [
            sys.executable,
            "scripts/memory_store.py",
            "--db",
            str(db_path),
            "add",
            "--kind",
            "notes",
            "--content",
            "Vector retrieval should return ranked summaries.",
            "--metadata",
            '{"phase": 4}',
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
        env=env,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/memory_store.py",
            "--db",
            str(db_path),
            "search",
            "--query",
            "ranked retrieval summaries",
            "--limit",
            "3",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload
    assert payload[0]["score"] > 0
