from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.memory_store import (
    add_memory_entry,
    get_recent_memories,
    prune_memory_entries,
    resolve_memory_max_entries,
    resolve_memory_retention_days,
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


def test_resolve_memory_controls_from_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "memory_retention_days: 21\nmemory_max_entries: 123\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(settings_path))
    monkeypatch.delenv("AI_LAN_MEMORY_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("AI_LAN_MEMORY_MAX_ENTRIES", raising=False)

    assert resolve_memory_retention_days() == 21
    assert resolve_memory_max_entries() == 123


def test_prune_memory_entries_enforces_max_entries(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    for index in range(5):
        add_memory_entry(
            kind="notes",
            content=f"note {index}",
            metadata={"index": index},
            db_path=db_path,
        )

    result = prune_memory_entries(db_path=db_path, max_entries=2, retention_days=365)
    assert result["status"] == "ok"
    assert result["pruned_count"] == 3

    remaining = get_recent_memories(db_path=db_path, limit=10)
    assert len(remaining) == 2


def test_prune_memory_entries_honors_retention_days(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="fresh memory",
        metadata={"age": "new"},
        db_path=db_path,
    )

    from tools.memory_store import _connect

    with _connect(db_path) as connection:
        connection.execute(
            "UPDATE memories SET created_at = ? WHERE id = 1",
            ("2000-01-01T00:00:00+00:00",),
        )
        connection.commit()

    add_memory_entry(
        kind="notes",
        content="latest memory",
        metadata={"age": "latest"},
        db_path=db_path,
    )

    result = prune_memory_entries(db_path=db_path, retention_days=30, max_entries=50)
    assert result["status"] == "ok"
    assert result["age_candidates"] >= 1

    remaining = get_recent_memories(db_path=db_path, limit=10)
    summaries = " ".join(entry.summary for entry in remaining).lower()
    assert "latest memory" in summaries
    assert "fresh memory" not in summaries


# ---------------------------------------------------------------------------
# Phase 3.1 — profile segmentation
# ---------------------------------------------------------------------------

def test_add_and_retrieve_with_profile(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Work task: review policy engine changes.",
        profile="work",
        db_path=db_path,
    )
    add_memory_entry(
        kind="notes",
        content="Home task: water the plants.",
        profile="home",
        db_path=db_path,
    )

    work_hits = retrieve_relevant_memories(query="policy review task", profile="work", db_path=db_path)
    home_hits = retrieve_relevant_memories(query="water plants", profile="home", db_path=db_path)

    assert work_hits
    assert all(hit.metadata.get("profile") == "work" for hit in work_hits)
    assert home_hits
    assert all(hit.metadata.get("profile") == "home" for hit in home_hits)


def test_profile_filter_excludes_other_profiles_from_retrieve(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Router schema validation is policy-gated.",
        profile="work",
        db_path=db_path,
    )
    add_memory_entry(
        kind="notes",
        content="Router schema validation is policy-gated.",
        profile="home",
        db_path=db_path,
    )

    work_hits = retrieve_relevant_memories(
        query="router schema policy", profile="work", db_path=db_path
    )
    assert all(hit.metadata.get("profile") == "work" for hit in work_hits)


def test_get_recent_memories_profile_filter(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(kind="notes", content="Work note one.", profile="work", db_path=db_path)
    add_memory_entry(kind="notes", content="Home note one.", profile="home", db_path=db_path)
    add_memory_entry(kind="notes", content="Home note two.", profile="home", db_path=db_path)

    home_recent = get_recent_memories(profile="home", db_path=db_path)
    assert len(home_recent) == 2
    assert all(e.metadata.get("profile") == "home" for e in home_recent)

    work_recent = get_recent_memories(profile="work", db_path=db_path)
    assert len(work_recent) == 1


# ---------------------------------------------------------------------------
# Phase 3.1 — retention automation CLI
# ---------------------------------------------------------------------------

def test_memory_retention_cli_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    output_path = tmp_path / "retention_report.json"
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "memory_retention_days: 365\nmemory_max_entries: 2000\n",
        encoding="utf-8",
    )

    import os

    env = {**os.environ, "AI_LAN_DEBUG": "0", "AI_LAN_TRACE": "0", "AI_LAN_PROFILE": "0"}

    for idx in range(3):
        add_memory_entry(
            kind="notes",
            content=f"dry run note {idx}",
            db_path=db_path,
        )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/memory_retention.py",
            "--db",
            str(db_path),
            "--settings",
            str(settings_path),
            "--output",
            str(output_path),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
        env=env,
    )

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert "pruned_count" in payload
    assert "DRY RUN" in result.stdout

    remaining = get_recent_memories(db_path=db_path, limit=10)
    assert len(remaining) == 3  # nothing deleted in dry run


def test_memory_retention_cli_prunes_overflow(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    output_path = tmp_path / "retention_report.json"
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "memory_retention_days: 365\nmemory_max_entries: 2000\n",
        encoding="utf-8",
    )

    import os

    env = {**os.environ, "AI_LAN_DEBUG": "0", "AI_LAN_TRACE": "0", "AI_LAN_PROFILE": "0"}

    for idx in range(5):
        add_memory_entry(
            kind="notes",
            content=f"overflow note {idx}",
            db_path=db_path,
        )

    subprocess.run(
        [
            sys.executable,
            "scripts/memory_retention.py",
            "--db",
            str(db_path),
            "--settings",
            str(settings_path),
            "--output",
            str(output_path),
            "--max-entries",
            "2",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
        env=env,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["pruned_count"] == 3
    remaining = get_recent_memories(db_path=db_path, limit=10)
    assert len(remaining) == 2
