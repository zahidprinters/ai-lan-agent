from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from memory.long_term.embeddings import cosine_similarity, embed_text
from tools.memory_store import get_memory_db_path, retrieve_relevant_memories, tokenize_text

ROOT = Path(__file__).resolve().parents[1]


@sentinel
def get_default_merged_corpus_path(merged_corpus_path: Path | None = None) -> Path:
    if merged_corpus_path is not None:
        return merged_corpus_path
    configured = os.getenv("AI_LAN_INGESTION_MERGED_PATH")
    if configured:
        return Path(configured)
    return ROOT / "temp" / "ingestion" / "merged_corpus.txt"


def _score_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    union = len(query_tokens | candidate_tokens)
    if union == 0:
        return 0.0
    return round(len(query_tokens & candidate_tokens) / union, 4)


@sentinel
def retrieve_corpus_snippets(
    *,
    query: str,
    merged_corpus_path: Path | None = None,
    limit: int = 5,
    min_score: float = 0.05,
) -> list[dict[str, Any]]:
    target_path = get_default_merged_corpus_path(merged_corpus_path)
    if not target_path.exists():
        return []

    query_tokens = set(tokenize_text(query))
    if not query_tokens:
        return []

    query_embedding = embed_text(query)

    scored: list[tuple[float, int, str, float, float]] = []
    for index, line in enumerate(target_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        token_score = _score_overlap(query_tokens, set(tokenize_text(stripped)))
        vector_score = cosine_similarity(query_embedding, embed_text(stripped))
        score = round((0.65 * vector_score) + (0.35 * token_score), 4)
        if score < min_score:
            continue
        scored.append((score, index, stripped, vector_score, token_score))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "score": score,
            "vector_score": vector_score,
            "token_score": token_score,
            "line_number": line_number,
            "text": text,
        }
        for score, line_number, text, vector_score, token_score in scored[:limit]
    ]


@sentinel
def build_prompt_context(
    *,
    query: str,
    memory_limit: int = 5,
    snippet_limit: int = 5,
    min_score: float = 0.05,
    memory_kind: str | None = None,
    memory_db_path: Path | None = None,
    memory_backend: str | None = None,
    chroma_path: Path | None = None,
    merged_corpus_path: Path | None = None,
) -> dict[str, Any]:
    memory_hits = retrieve_relevant_memories(
        query=query,
        limit=memory_limit,
        min_score=min_score,
        kind=memory_kind,
        db_path=get_memory_db_path(memory_db_path),
        memory_backend=memory_backend,
        chroma_path=chroma_path,
    )
    snippet_hits = retrieve_corpus_snippets(
        query=query,
        merged_corpus_path=merged_corpus_path,
        limit=snippet_limit,
        min_score=min_score,
    )

    memory_lines = [f"- [{hit.score}] {hit.summary}" for hit in memory_hits]
    snippet_lines = [f"- [{item['score']}] {item['text']}" for item in snippet_hits]
    context_lines = [
        f"Query: {query}",
        "",
        "Relevant Memory:",
        *(memory_lines or ["- none"]),
        "",
        "Relevant Corpus Snippets:",
        *(snippet_lines or ["- none"]),
    ]

    return {
        "query": query,
        "memory_hits": [hit.to_dict() for hit in memory_hits],
        "corpus_snippets": snippet_hits,
        "context_text": "\n".join(context_lines).strip(),
    }
