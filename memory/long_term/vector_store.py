from __future__ import annotations

"""Lightweight persistent vector index for local semantic retrieval."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from memory.long_term.embeddings import EMBEDDING_DIM, cosine_similarity, embed_text

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VECTOR_INDEX = ROOT / "temp" / "memory" / "memory_store.vectors.json"


@dataclass(frozen=True)
class VectorRecord:
    key: str
    text: str
    embedding: list[float]
    metadata: dict[str, object]
    updated_at: str


@dataclass(frozen=True)
class VectorHit:
    key: str
    score: float
    text: str
    metadata: dict[str, object]
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _resolve_vector_index_path(path: Path | None = None) -> Path:
    if path is None:
        return DEFAULT_VECTOR_INDEX
    if path.suffix:
        return path.with_suffix(".vectors.json")
    return path / "vectors.json"


def _load_records(path: Path) -> dict[str, VectorRecord]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    raw_records: Any
    if isinstance(payload, dict):
        raw_records = payload.get("records", payload)
    else:
        raw_records = payload

    records: dict[str, VectorRecord] = {}
    if isinstance(raw_records, dict):
        for key, value in raw_records.items():
            if not isinstance(value, dict):
                continue
            record_key = str(value.get("key", key)).strip()
            if not record_key:
                continue
            records[record_key] = VectorRecord(
                key=record_key,
                text=str(value.get("text", "")),
                embedding=[
                    float(item)
                    for item in value.get("embedding", [])
                    if isinstance(item, (int, float))
                ],
                metadata=(
                    value.get("metadata", {}) if isinstance(value.get("metadata"), dict) else {}
                ),
                updated_at=str(value.get("updated_at", "")),
            )
        return records

    if isinstance(raw_records, list):
        for value in raw_records:
            if not isinstance(value, dict):
                continue
            record_key = str(value.get("key", "")).strip()
            if not record_key:
                continue
            records[record_key] = VectorRecord(
                key=record_key,
                text=str(value.get("text", "")),
                embedding=[
                    float(item)
                    for item in value.get("embedding", [])
                    if isinstance(item, (int, float))
                ],
                metadata=(
                    value.get("metadata", {}) if isinstance(value.get("metadata"), dict) else {}
                ),
                updated_at=str(value.get("updated_at", "")),
            )
    return records


class VectorStore:
    def __init__(self, path: Path | None = None, *, dimension: int = EMBEDDING_DIM) -> None:
        self.path = _resolve_vector_index_path(path)
        self.dimension = dimension
        self._records = _load_records(self.path)

    def __len__(self) -> int:
        return len(self._records)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dimension": self.dimension,
            "records": [
                asdict(record)
                for record in sorted(self._records.values(), key=lambda item: item.key)
            ],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def upsert(
        self, key: str, text: str, metadata: dict[str, object] | None = None
    ) -> VectorRecord:
        normalized_key = str(key).strip()
        if not normalized_key:
            raise ValueError("Vector store key must be non-empty.")
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Vector store text must be non-empty.")

        record = VectorRecord(
            key=normalized_key,
            text=normalized_text,
            embedding=embed_text(normalized_text, dimension=self.dimension),
            metadata=metadata or {},
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._records[normalized_key] = record
        self._save()
        return record

    def query_hits(
        self,
        query_text: str,
        *,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[VectorHit]:
        normalized_query = query_text.strip()
        if not normalized_query:
            return []

        query_embedding = embed_text(normalized_query, dimension=self.dimension)
        hits: list[VectorHit] = []
        for record in self._records.values():
            score = cosine_similarity(query_embedding, record.embedding)
            if score < min_score:
                continue
            hits.append(
                VectorHit(
                    key=record.key,
                    score=round(score, 4),
                    text=record.text,
                    metadata=record.metadata,
                    updated_at=record.updated_at,
                )
            )

        hits.sort(key=lambda item: (-item.score, item.updated_at, item.key))
        return hits[: max(limit, 0)]

    def query(self, query_text: str, limit: int = 5) -> list[str]:
        return [hit.key for hit in self.query_hits(query_text, limit=limit)]

    def clear(self) -> None:
        self._records.clear()
        if self.path.exists():
            self.path.unlink()


@lru_cache(maxsize=32)
def get_vector_store(path: Path | None = None) -> VectorStore:
    return VectorStore(path)


__all__ = [
    "DEFAULT_VECTOR_INDEX",
    "VectorHit",
    "VectorRecord",
    "VectorStore",
    "get_vector_store",
]
