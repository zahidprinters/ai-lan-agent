from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from debug_utils import sentinel

from memory.long_term.embeddings import cosine_similarity, embed_text
from memory.long_term.vector_store import get_vector_store

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_DB = ROOT / "temp" / "memory" / "memory_store.sqlite3"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class MemoryEntry:
    memory_id: int
    kind: str
    content: str
    summary: str
    metadata: dict[str, object]
    created_at: str


@dataclass(frozen=True)
class MemoryHit:
    memory_id: int
    score: float
    kind: str
    summary: str
    created_at: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@sentinel
def get_memory_db_path(db_path: Path | None = None) -> Path:
    return db_path or DEFAULT_MEMORY_DB


@sentinel
def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    resolved_path = get_memory_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    return connection


@sentinel
def init_memory_store(db_path: Path | None = None) -> Path:
    resolved_path = get_memory_db_path(db_path)
    with _connect(resolved_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT NOT NULL,
                tokens_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_kind_created_at ON memories(kind, created_at DESC)"
        )
        connection.commit()
    return resolved_path


@sentinel
def tokenize_text(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


@sentinel
def summarize_text(text: str, max_chars: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


@sentinel
def summarize_entries(entries: list[str], max_chars: int = 220) -> str:
    """Compatibility helper that summarizes a list of memory strings."""
    merged = "\n".join(item.strip() for item in entries if item and item.strip())
    return summarize_text(merged, max_chars=max_chars)


@sentinel
def add_memory_entry(
    *,
    kind: str,
    content: str,
    metadata: dict[str, object] | None = None,
    db_path: Path | None = None,
) -> MemoryEntry:
    if not kind.strip():
        raise ValueError("Memory kind must be non-empty.")
    if not content.strip():
        raise ValueError("Memory content must be non-empty.")

    init_memory_store(db_path)
    created_at = datetime.now(timezone.utc).isoformat()
    tokens = tokenize_text(content)
    summary = summarize_text(content)
    metadata_payload = metadata or {}

    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO memories(kind, content, summary, tokens_json, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                kind.strip().lower(),
                content,
                summary,
                json.dumps(tokens, ensure_ascii=True),
                json.dumps(metadata_payload, ensure_ascii=True),
                created_at,
            ),
        )
        connection.commit()
        last_row_id = cursor.lastrowid
        if last_row_id is None:
            raise RuntimeError("Failed to persist memory entry.")
        memory_id = int(last_row_id)

    try:
        vector_store = get_vector_store(db_path)
        vector_store.upsert(
            str(memory_id),
            f"{summary}\n{content}",
            metadata={"kind": kind.strip().lower(), **metadata_payload},
        )
    except Exception:
        pass

    return MemoryEntry(
        memory_id=memory_id,
        kind=kind.strip().lower(),
        content=content,
        summary=summary,
        metadata=metadata_payload,
        created_at=created_at,
    )


@sentinel
def store_conversation_summary(
    *,
    user_text: str,
    assistant_text: str,
    metadata: dict[str, object] | None = None,
    db_path: Path | None = None,
) -> MemoryEntry:
    content = f"User: {user_text.strip()}\n" f"Assistant: {assistant_text.strip()}"
    merged_metadata = {"source": "conversation", **(metadata or {})}
    return add_memory_entry(
        kind="conversation",
        content=content,
        metadata=merged_metadata,
        db_path=db_path,
    )


def _score_token_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    intersection = len(query_tokens & candidate_tokens)
    union = len(query_tokens | candidate_tokens)
    if union == 0:
        return 0.0
    return round(intersection / union, 4)


@sentinel
def retrieve_relevant_memories(
    *,
    query: str,
    limit: int = 5,
    min_score: float = 0.05,
    kind: str | None = None,
    db_path: Path | None = None,
) -> list[MemoryHit]:
    init_memory_store(db_path)
    query_tokens = set(tokenize_text(query))
    if not query_tokens:
        return []

    query_embedding = embed_text(query)
    vector_score_map: dict[int, float] = {}
    try:
        vector_store = get_vector_store(db_path)
        vector_score_map = {
            int(hit.key): hit.score
            for hit in vector_store.query_hits(query, limit=max(limit * 4, 20), min_score=0.0)
            if str(hit.key).strip().isdigit()
        }
    except Exception:
        vector_score_map = {}

    sql = "SELECT id, kind, content, summary, tokens_json, metadata_json, created_at FROM memories"
    params: tuple[object, ...] = ()
    if kind:
        sql += " WHERE kind = ?"
        params = (kind.strip().lower(),)
    sql += " ORDER BY created_at DESC"

    hits: list[MemoryHit] = []
    with _connect(db_path) as connection:
        for row in connection.execute(sql, params):
            memory_id = int(row["id"])
            content = str(row["content"])
            summary = str(row["summary"])
            tokens = set(json.loads(row["tokens_json"]))
            token_score = _score_token_overlap(query_tokens, tokens)
            vector_score = vector_score_map.get(memory_id)
            if vector_score is None:
                vector_score = cosine_similarity(
                    query_embedding, embed_text(f"{summary}\n{content}")
                )
            score = round((0.65 * vector_score) + (0.35 * token_score), 4)
            if score < min_score:
                continue
            hits.append(
                MemoryHit(
                    memory_id=memory_id,
                    score=score,
                    kind=str(row["kind"]),
                    summary=summary,
                    created_at=str(row["created_at"]),
                    metadata=json.loads(row["metadata_json"]),
                )
            )

    hits.sort(key=lambda item: (item.score, item.created_at), reverse=True)
    return hits[:limit]


@sentinel
def get_recent_memories(
    *,
    limit: int = 10,
    kind: str | None = None,
    db_path: Path | None = None,
) -> list[MemoryEntry]:
    init_memory_store(db_path)
    sql = "SELECT id, kind, content, summary, metadata_json, created_at FROM memories"
    params: tuple[object, ...] = ()
    if kind:
        sql += " WHERE kind = ?"
        params = (kind.strip().lower(),)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params = (*params, limit)

    entries: list[MemoryEntry] = []
    with _connect(db_path) as connection:
        for row in connection.execute(sql, params):
            entries.append(
                MemoryEntry(
                    memory_id=int(row["id"]),
                    kind=str(row["kind"]),
                    content=str(row["content"]),
                    summary=str(row["summary"]),
                    metadata=json.loads(row["metadata_json"]),
                    created_at=str(row["created_at"]),
                )
            )
    return entries
