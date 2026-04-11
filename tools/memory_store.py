from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from memory.long_term.embeddings import cosine_similarity, embed_text
from memory.long_term.chroma_store import chroma_upsert, query_chroma_vector_scores
from memory.long_term.vector_store import get_vector_store

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_DB = ROOT / "temp" / "memory" / "memory_store.sqlite3"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
SUPPORTED_MEMORY_BACKENDS = {"none", "chroma"}
DEFAULT_MEMORY_RETENTION_DAYS = 30
DEFAULT_MEMORY_MAX_ENTRIES = 2000


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
def resolve_memory_backend(memory_backend: str | None = None) -> str:
    selected = (memory_backend or os.getenv("AI_LAN_MEMORY_BACKEND", "none")).strip().lower()
    if selected not in SUPPORTED_MEMORY_BACKENDS:
        return "none"
    return selected


@sentinel
def resolve_chroma_path(chroma_path: Path | None = None) -> Path | None:
    if chroma_path is not None:
        return chroma_path
    configured = os.getenv("AI_LAN_CHROMA_PATH", "").strip()
    return Path(configured) if configured else None


def _coerce_scalar(value: str) -> object:
    normalized = value.strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"1", "0"}:
        return lowered == "1"
    try:
        if any(char in normalized for char in {".", "e", "E"}):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized.strip('"').strip("'")


def _load_settings_values() -> dict[str, object]:
    settings_path = Path(
        os.getenv("AI_LAN_SETTINGS_PATH", str(ROOT / "config" / "settings.yaml"))
    )
    if not settings_path.exists():
        return {}

    values: dict[str, object] = {}
    for raw_line in settings_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)
    return values


def _coerce_positive_int(value: object, *, default: int, minimum: int = 1) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, numeric)


@sentinel
def resolve_memory_retention_days(retention_days: int | None = None) -> int:
    if retention_days is not None:
        return _coerce_positive_int(retention_days, default=DEFAULT_MEMORY_RETENTION_DAYS)

    env_value = os.getenv("AI_LAN_MEMORY_RETENTION_DAYS", "").strip()
    if env_value:
        return _coerce_positive_int(env_value, default=DEFAULT_MEMORY_RETENTION_DAYS)

    settings_values = _load_settings_values()
    configured = settings_values.get("memory_retention_days", DEFAULT_MEMORY_RETENTION_DAYS)
    return _coerce_positive_int(configured, default=DEFAULT_MEMORY_RETENTION_DAYS)


@sentinel
def resolve_memory_max_entries(max_entries: int | None = None) -> int:
    if max_entries is not None:
        return _coerce_positive_int(max_entries, default=DEFAULT_MEMORY_MAX_ENTRIES)

    env_value = os.getenv("AI_LAN_MEMORY_MAX_ENTRIES", "").strip()
    if env_value:
        return _coerce_positive_int(env_value, default=DEFAULT_MEMORY_MAX_ENTRIES)

    settings_values = _load_settings_values()
    configured = settings_values.get("memory_max_entries", DEFAULT_MEMORY_MAX_ENTRIES)
    return _coerce_positive_int(configured, default=DEFAULT_MEMORY_MAX_ENTRIES)


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
    memory_backend: str | None = None,
    chroma_path: Path | None = None,
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

    if resolve_memory_backend(memory_backend) == "chroma":
        chroma_upsert(
            key=str(memory_id),
            text=f"{summary}\n{content}",
            metadata={"kind": kind.strip().lower(), **metadata_payload},
            chroma_path=resolve_chroma_path(chroma_path),
        )

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
    memory_backend: str | None = None,
    chroma_path: Path | None = None,
) -> MemoryEntry:
    content = f"User: {user_text.strip()}\n" f"Assistant: {assistant_text.strip()}"
    merged_metadata = {"source": "conversation", **(metadata or {})}
    return add_memory_entry(
        kind="conversation",
        content=content,
        metadata=merged_metadata,
        db_path=db_path,
        memory_backend=memory_backend,
        chroma_path=chroma_path,
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
    memory_backend: str | None = None,
    chroma_path: Path | None = None,
) -> list[MemoryHit]:
    init_memory_store(db_path)
    query_tokens = set(tokenize_text(query))
    if not query_tokens:
        return []

    query_embedding = embed_text(query)
    vector_score_map: dict[int, float] = {}
    backend = resolve_memory_backend(memory_backend)
    if backend == "chroma":
        vector_score_map = query_chroma_vector_scores(
            query=query,
            limit=max(limit * 4, 20),
            min_score=0.0,
            chroma_path=resolve_chroma_path(chroma_path),
        )

    if not vector_score_map:
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


@sentinel
def prune_memory_entries(
    *,
    db_path: Path | None = None,
    retention_days: int | None = None,
    max_entries: int | None = None,
    kind: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    init_memory_store(db_path)
    resolved_retention_days = resolve_memory_retention_days(retention_days)
    resolved_max_entries = resolve_memory_max_entries(max_entries)

    filters = ""
    params: list[object] = []
    normalized_kind = (kind or "").strip().lower()
    if normalized_kind:
        filters = " WHERE kind = ?"
        params.append(normalized_kind)

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=resolved_retention_days)
    cutoff_iso = cutoff.isoformat()

    age_ids: list[int] = []
    overflow_ids: list[int] = []
    with _connect(db_path) as connection:
        age_sql = f"SELECT id FROM memories{filters}{' AND' if filters else ' WHERE'} created_at < ?"
        age_params = [*params, cutoff_iso]
        age_ids = [int(row["id"]) for row in connection.execute(age_sql, tuple(age_params))]

        count_sql = f"SELECT COUNT(*) as total FROM memories{filters}"
        total_count = int(connection.execute(count_sql, tuple(params)).fetchone()["total"])
        overflow = max(0, total_count - resolved_max_entries)
        if overflow > 0:
            overflow_sql = (
                f"SELECT id FROM memories{filters} ORDER BY created_at ASC LIMIT ?"
            )
            overflow_ids = [
                int(row["id"])
                for row in connection.execute(overflow_sql, tuple([*params, overflow]))
            ]

        pruned_ids = sorted(set(age_ids) | set(overflow_ids))
        if not dry_run and pruned_ids:
            placeholders = ",".join("?" for _ in pruned_ids)
            connection.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", tuple(pruned_ids))
            connection.commit()

    return {
        "status": "ok",
        "kind": normalized_kind or "all",
        "dry_run": dry_run,
        "retention_days": resolved_retention_days,
        "max_entries": resolved_max_entries,
        "age_candidates": len(age_ids),
        "overflow_candidates": len(overflow_ids),
        "pruned_count": len(sorted(set(age_ids) | set(overflow_ids))),
    }


__all__ = [
    "DEFAULT_MEMORY_DB",
    "DEFAULT_MEMORY_MAX_ENTRIES",
    "DEFAULT_MEMORY_RETENTION_DAYS",
    "MemoryEntry",
    "MemoryHit",
    "add_memory_entry",
    "get_memory_db_path",
    "get_recent_memories",
    "init_memory_store",
    "prune_memory_entries",
    "resolve_chroma_path",
    "resolve_memory_backend",
    "resolve_memory_max_entries",
    "resolve_memory_retention_days",
    "retrieve_relevant_memories",
    "store_conversation_summary",
    "summarize_entries",
    "summarize_text",
    "tokenize_text",
]
