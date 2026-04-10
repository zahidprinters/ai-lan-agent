from __future__ import annotations

"""Optional ChromaDB facade for long-term memory embeddings."""

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from memory.long_term.embeddings import EMBEDDING_DIM, embed_text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA_PATH = ROOT / "temp" / "chroma"
DEFAULT_COLLECTION_NAME = "ai_lan_memory"


def _resolve_chroma_path(chroma_path: Path | None = None) -> Path:
    if chroma_path is not None:
        return chroma_path
    configured = os.getenv("AI_LAN_CHROMA_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_CHROMA_PATH


def _sanitize_metadata(metadata: dict[str, object] | None = None) -> dict[str, object]:
    if not metadata:
        return {}
    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[str(key)] = value
        else:
            sanitized[str(key)] = str(value)
    return sanitized


class _LocalEmbeddingFunction:
    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return [embed_text(text, dimension=EMBEDDING_DIM) for text in input]


def _score_from_distance(distance: object) -> float:
    try:
        numeric = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, 1.0 - numeric), 4)


@lru_cache(maxsize=16)
def _get_collection(chroma_path: Path, collection_name: str) -> Any:
    import chromadb  # type: ignore[import-untyped]

    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=_LocalEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


@sentinel
def chroma_upsert(
    *,
    key: str,
    text: str,
    metadata: dict[str, object] | None = None,
    chroma_path: Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> bool:
    try:
        collection = _get_collection(_resolve_chroma_path(chroma_path), collection_name)
        collection.upsert(
            ids=[str(key)],
            documents=[text],
            metadatas=[_sanitize_metadata(metadata)],
        )
    except Exception:
        return False
    return True


@sentinel
def query_chroma_vector_scores(
    *,
    query: str,
    limit: int,
    min_score: float = 0.0,
    chroma_path: Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> dict[int, float]:
    if not query.strip() or limit <= 0:
        return {}

    try:
        collection = _get_collection(_resolve_chroma_path(chroma_path), collection_name)
        result = collection.query(
            query_texts=[query],
            n_results=max(limit, 1),
            include=["distances"],
        )
    except Exception:
        return {}

    ids = result.get("ids", [[]])
    distances = result.get("distances", [[]])
    if not isinstance(ids, list) or not ids:
        return {}

    first_ids = ids[0] if isinstance(ids[0], list) else []
    first_distances = distances[0] if isinstance(distances, list) and distances else []

    score_map: dict[int, float] = {}
    for index, item in enumerate(first_ids):
        key = str(item).strip()
        if not key.isdigit():
            continue
        distance = first_distances[index] if index < len(first_distances) else 1.0
        score = _score_from_distance(distance)
        if score < min_score:
            continue
        score_map[int(key)] = score
    return score_map


__all__ = [
    "DEFAULT_CHROMA_PATH",
    "chroma_upsert",
    "query_chroma_vector_scores",
]