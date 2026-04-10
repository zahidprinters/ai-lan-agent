"""Runtime context composition for agent execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from memory.short_term.buffer import ShortTermBuffer
from tools.context_builder import build_prompt_context


def _truncate_preserving_tail(text: str, max_chars: int) -> str:
    normalized = text.strip()
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    kept = normalized[-max_chars:]
    return "...\n" + kept


def build_runtime_context(
    *,
    query: str,
    short_term_buffer: ShortTermBuffer | None = None,
    memory_limit: int = 5,
    snippet_limit: int = 5,
    min_score: float = 0.05,
    memory_kind: str | None = None,
    memory_db_path: Path | None = None,
    memory_backend: str | None = None,
    chroma_path: Path | None = None,
    perception_summary: str | None = None,
    max_context_chars: int = 4000,
    merged_corpus_path: Path | None = None,
) -> dict[str, Any]:
    retrieval_context = build_prompt_context(
        query=query,
        memory_limit=memory_limit,
        snippet_limit=snippet_limit,
        min_score=min_score,
        memory_kind=memory_kind,
        memory_db_path=memory_db_path,
        memory_backend=memory_backend,
        chroma_path=chroma_path,
        merged_corpus_path=merged_corpus_path,
    )

    short_term_text = "(no short-term context)"
    if short_term_buffer is not None:
        short_term_text = short_term_buffer.to_context_text()
    short_term_text = _truncate_preserving_tail(short_term_text, max_context_chars)

    perception_text = (perception_summary or "").strip() or "(no live perception context)"
    perception_text = _truncate_preserving_tail(perception_text, max_context_chars)
    retrieved_text = str(retrieval_context.get("context_text", "")).strip() or "(none)"
    retrieved_text = _truncate_preserving_tail(retrieved_text, max_context_chars)

    assembled_text = "\n\n".join(
        [
            f"Runtime Query: {query}",
            "Short-Term Context:",
            short_term_text,
            "Perception Context:",
            perception_text,
            "Retrieved Context:",
            retrieved_text,
        ]
    ).strip()

    return {
        "query": query,
        "short_term_context": short_term_text,
        "perception_summary": perception_text,
        "retrieval": retrieval_context,
        "assembled_context": assembled_text,
    }


__all__ = ["build_runtime_context", "build_prompt_context"]
