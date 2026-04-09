from __future__ import annotations

from pathlib import Path

from memory.long_term.vector_store import VectorStore


def test_vector_store_upsert_query_and_persistence(tmp_path: Path) -> None:
    index_path = tmp_path / "memory.sqlite3"
    store = VectorStore(index_path)
    store.upsert(
        "1", "Typing actions require confirmation before execution.", metadata={"kind": "notes"}
    )
    store.upsert("2", "The garden hose is green.", metadata={"kind": "notes"})

    hits = store.query_hits("approval to enter text")
    assert hits
    assert hits[0].key == "1"
    assert hits[0].score > hits[-1].score

    reloaded = VectorStore(index_path)
    keys = reloaded.query("approval to enter text", limit=2)
    assert keys[0] == "1"
