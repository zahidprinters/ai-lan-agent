from __future__ import annotations

"""Local vector embedding helpers for lightweight semantic retrieval."""

from hashlib import blake2b
import re

import numpy as np

from debug_utils import sentinel

EMBEDDING_DIM = 256
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

_ALIASES = {
    "confirm": {
        "confirm",
        "confirmation",
        "confirmed",
        "confirming",
        "approve",
        "approval",
        "authorized",
        "authorize",
        "authorization",
    },
    "context": {"context", "prompt", "history", "session", "state"},
    "docs": {"doc", "docs", "document", "documents", "documentation"},
    "memory": {"memory", "memories", "remember", "remembered", "recall", "retrieval", "retrieve"},
    "model": {"model", "models", "neural", "brain", "llm", "transformer"},
    "policy": {"policy", "safety", "guard", "guardrail", "rules", "rule"},
    "search": {"search", "searching", "find", "finding", "lookup", "look", "query"},
    "system": {"system", "systems", "ops", "operation", "operations", "control", "controls"},
    "type": {"type", "typing", "typed", "enter", "entering", "input", "text"},
    "tool": {"tool", "tools", "action", "actions", "agent", "agents", "router"},
}

_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in _ALIASES.items() for alias in aliases}


def _strip_suffixes(token: str) -> str:
    for suffix in (
        "ization",
        "ication",
        "ation",
        "tion",
        "ments",
        "ment",
        "ing",
        "ers",
        "er",
        "ied",
        "ies",
        "ed",
        "ly",
        "s",
    ):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


@sentinel
def normalize_token(token: str) -> str:
    lowered = token.strip().lower()
    if not lowered:
        return ""
    if lowered in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[lowered]
    stripped = _strip_suffixes(lowered)
    if stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]
    return stripped or lowered


@sentinel
def tokenize_embedding_text(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_PATTERN.findall(text.lower()):
        normalized = normalize_token(raw)
        if not normalized or normalized in _STOPWORDS:
            continue
        tokens.append(normalized)
    return tokens


def _feature_tokens(tokens: list[str]) -> list[str]:
    features = list(tokens)
    features.extend(f"bi:{left}_{right}" for left, right in zip(tokens, tokens[1:]))
    for token in tokens:
        if len(token) < 4:
            continue
        features.extend(f"tri:{token[index:index + 3]}" for index in range(len(token) - 2))
    return features


def _hash_feature(feature: str, dimension: int) -> int:
    digest = blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % max(dimension, 1)


@sentinel
def embed_text(text: str, *, dimension: int = EMBEDDING_DIM) -> list[float]:
    if dimension <= 0:
        raise ValueError("dimension must be positive")

    tokens = tokenize_embedding_text(text)
    vector = np.zeros(dimension, dtype=np.float32)
    if not tokens:
        return vector.tolist()

    for feature in _feature_tokens(tokens):
        index = _hash_feature(feature, dimension)
        weight = 1.0
        if feature.startswith("bi:"):
            weight = 1.15
        elif feature.startswith("tri:"):
            weight = 0.35
        vector[index] += weight

    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector /= norm
    return vector.astype(np.float32).tolist()


@sentinel
def cosine_similarity(
    left: list[float] | tuple[float, ...], right: list[float] | tuple[float, ...]
) -> float:
    left_array = np.asarray(left, dtype=np.float32)
    right_array = np.asarray(right, dtype=np.float32)
    if left_array.size == 0 or right_array.size == 0:
        return 0.0
    if left_array.shape != right_array.shape:
        raise ValueError("Vectors must have the same dimension for cosine similarity.")

    left_norm = float(np.linalg.norm(left_array))
    right_norm = float(np.linalg.norm(right_array))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(np.dot(left_array, right_array) / (left_norm * right_norm))


__all__ = [
    "EMBEDDING_DIM",
    "cosine_similarity",
    "embed_text",
    "normalize_token",
    "tokenize_embedding_text",
]
