"""Runtime context composition for agent execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from memory.short_term.buffer import ShortTermBuffer
from tools.context_builder import build_prompt_context

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SENSITIVE_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "password",
    "passcode",
    "otp",
    "2fa",
    "bank",
    "payment",
    "wallet",
    "credit card",
    "ssn",
    "private key",
    "token",
    "credential",
    "invoice",
)


def _truncate_preserving_tail(text: str, max_chars: int) -> str:
    normalized = text.strip()
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    kept = normalized[-max_chars:]
    return "...\n" + kept


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


def _load_sensitive_context_settings() -> tuple[bool, tuple[str, ...]]:
    values = _load_settings_values()

    enabled_raw = values.get("dynamic_safety_enabled", False)
    if isinstance(enabled_raw, bool):
        enabled = enabled_raw
    elif isinstance(enabled_raw, (int, float)):
        enabled = bool(enabled_raw)
    elif isinstance(enabled_raw, str):
        enabled = enabled_raw.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = False

    keywords_raw = values.get("sensitive_context_keywords")
    keywords: tuple[str, ...] = ()
    if isinstance(keywords_raw, str):
        keywords = tuple(
            part.strip().lower() for part in keywords_raw.split(",") if part.strip()
        )
    if not keywords:
        keywords = DEFAULT_SENSITIVE_CONTEXT_KEYWORDS

    return enabled, keywords


def _infer_sensitive_context(query: str, perception_summary: str | None) -> bool:
    enabled, keywords = _load_sensitive_context_settings()
    if not enabled:
        return False

    haystack = f"{query} {perception_summary or ''}".lower()
    return any(keyword in haystack for keyword in keywords)


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
    perception_source: str | None = None,
    perception_confidence: float | None = None,
    perception_ocr_backend: str | None = None,
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
    perception_source_text = (perception_source or "screen_ocr").strip() or "screen_ocr"
    perception_ocr_backend_text = (
        (perception_ocr_backend or "tesseract").strip().lower() or "tesseract"
    )
    confidence_text = (
        f" ({perception_confidence:.1f}% confidence)"
        if isinstance(perception_confidence, (int, float))
        else ""
    )
    retrieved_text = str(retrieval_context.get("context_text", "")).strip() or "(none)"
    retrieved_text = _truncate_preserving_tail(retrieved_text, max_context_chars)

    assembled_text = "\n\n".join(
        [
            f"Runtime Query: {query}",
            "Short-Term Context:",
            short_term_text,
            "Perception Context:",
            f"Source: {perception_source_text}{confidence_text}",
            f"OCR Backend: {perception_ocr_backend_text}",
            perception_text,
            "Retrieved Context:",
            retrieved_text,
        ]
    ).strip()

    sensitive_context = _infer_sensitive_context(query, perception_summary)

    return {
        "query": query,
        "short_term_context": short_term_text,
        "perception_summary": perception_text,
        "perception_source": perception_source_text,
        "perception_confidence": perception_confidence,
        "perception_ocr_backend": perception_ocr_backend_text,
        "sensitive_context": sensitive_context,
        "retrieval": retrieval_context,
        "assembled_context": assembled_text,
    }


__all__ = ["build_runtime_context", "build_prompt_context"]
