from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest

from tools.memory_store import add_memory_entry, retrieve_relevant_memories, resolve_memory_backend


class _FakeCollection:
    def __init__(self) -> None:
        self._documents: dict[str, str] = {}

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict[str, object]]) -> None:
        for key, text in zip(ids, documents):
            self._documents[key] = text

    def query(self, query_texts: list[str], n_results: int, include: list[str]) -> dict[str, object]:
        del query_texts, include
        ordered_ids = sorted(self._documents.keys())[:n_results]
        distances = [0.02 for _ in ordered_ids]
        return {"ids": [ordered_ids], "distances": [distances]}


class _FakeClient:
    def __init__(self, path: str) -> None:
        self.path = path
        self.collection = _FakeCollection()

    def get_or_create_collection(self, **kwargs: object) -> _FakeCollection:
        del kwargs
        return self.collection


def test_memory_backend_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_MEMORY_BACKEND", "chroma")
    assert resolve_memory_backend(None) == "chroma"
    assert resolve_memory_backend("unsupported") == "none"


def test_chroma_backend_retrieval_uses_chroma_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_module = types.SimpleNamespace(PersistentClient=_FakeClient)
    monkeypatch.setitem(sys.modules, "chromadb", fake_module)

    db_path = tmp_path / "memory.sqlite3"
    chroma_path = tmp_path / "chroma"

    add_memory_entry(
        kind="notes",
        content="Typing actions require explicit confirmation before execution.",
        metadata={"phase": "4.5"},
        db_path=db_path,
        memory_backend="chroma",
        chroma_path=chroma_path,
    )

    hits = retrieve_relevant_memories(
        query="confirmation for typing",
        db_path=db_path,
        memory_backend="chroma",
        chroma_path=chroma_path,
    )

    assert hits
    assert hits[0].score > 0
    assert "typing actions" in hits[0].summary.lower()
