from __future__ import annotations

from pathlib import Path

from tools.context_builder import build_prompt_context, retrieve_corpus_snippets
from tools.memory_store import add_memory_entry


def test_retrieve_corpus_snippets_returns_ranked_matches(tmp_path: Path) -> None:
    merged_path = tmp_path / "merged.txt"
    merged_path.write_text(
        "typing actions should require confirmation\n"
        "trusted ingestion improves context quality\n"
        "completely unrelated line\n",
        encoding="utf-8",
    )

    snippets = retrieve_corpus_snippets(
        query="typing confirmation policy",
        merged_corpus_path=merged_path,
        limit=2,
    )

    assert snippets
    assert snippets[0]["score"] > 0
    assert "typing" in snippets[0]["text"]


def test_retrieve_corpus_snippets_uses_hybrid_similarity(tmp_path: Path) -> None:
    merged_path = tmp_path / "merged.txt"
    merged_path.write_text(
        "typing actions should require confirmation\n" "garden notes about watering plants\n",
        encoding="utf-8",
    )

    snippets = retrieve_corpus_snippets(
        query="approval to enter text",
        merged_corpus_path=merged_path,
        limit=2,
    )

    assert snippets
    assert "typing" in snippets[0]["text"]
    assert snippets[0]["vector_score"] >= snippets[0]["token_score"]


def test_build_prompt_context_combines_memory_and_corpus(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    merged_path = tmp_path / "merged.txt"
    merged_path.write_text(
        "agent policy includes confirmation gates for typing\n"
        "retrieval should add relevant snippets to context\n",
        encoding="utf-8",
    )
    add_memory_entry(
        kind="notes",
        content="Typing actions need confirmation before execution.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    context = build_prompt_context(
        query="typing confirmation",
        memory_db_path=db_path,
        merged_corpus_path=merged_path,
    )

    assert context["memory_hits"]
    assert context["corpus_snippets"]
    assert "Relevant Memory:" in context["context_text"]
    assert "Relevant Corpus Snippets:" in context["context_text"]
