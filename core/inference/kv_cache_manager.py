from __future__ import annotations

import os
from dataclasses import dataclass


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


@dataclass(frozen=True)
class KVCachePolicy:
    max_turns: int = 8
    summary_enabled: bool = True
    summary_target_tokens: int = 160
    runtime_context_max_chars: int = 1200

    @classmethod
    def from_env(cls) -> "KVCachePolicy":
        return cls(
            max_turns=_env_int("AI_LAN_KV_CACHE_MAX_TURNS", 8),
            summary_enabled=_env_bool("AI_LAN_CONTEXT_SUMMARY_ENABLED", True),
            summary_target_tokens=_env_int("AI_LAN_CONTEXT_SUMMARY_TARGET_TOKENS", 160),
            runtime_context_max_chars=_env_int("AI_LAN_RUNTIME_CONTEXT_MAX_CHARS", 1200),
        )

    def should_compact(self, item_count: int) -> bool:
        return self.summary_enabled and item_count > self.max_turns

    def summarize_lines(self, lines: list[str], *, prefix: str) -> str:
        if not lines:
            return ""
        normalized = [_normalize_text(line) for line in lines if _normalize_text(line)]
        if not normalized:
            return ""

        max_chars = max(80, self.summary_target_tokens * 5)
        head_count = min(2, len(normalized))
        tail_count = 0 if len(normalized) <= 2 else min(2, len(normalized) - head_count)
        head = normalized[:head_count]
        tail = normalized[-tail_count:] if tail_count else []
        omitted = max(0, len(normalized) - len(head) - len(tail))

        parts: list[str] = [f"{prefix} ({len(normalized)} items)"]
        if head:
            parts.append("earliest: " + " | ".join(head))
        if omitted:
            parts.append(f"{omitted} intermediate items omitted")
        if tail:
            parts.append("latest: " + " | ".join(tail))

        summary = "; ".join(parts)
        if len(summary) <= max_chars:
            return summary
        return summary[: max_chars - 3].rstrip() + "..."

    def compact_runtime_context(self, text: str) -> tuple[str, str]:
        normalized = text.strip()
        if not normalized:
            return "", ""
        max_chars = max(120, self.runtime_context_max_chars)
        if not self.summary_enabled or len(normalized) <= max_chars:
            return normalized, ""

        lines = [line.rstrip() for line in normalized.splitlines() if line.strip()]
        if len(lines) <= 4:
            clipped = normalized[: max_chars - 3].rstrip() + "..."
            return clipped, "Runtime context compacted to fit prompt budget."

        candidate_sizes = [(3, 3), (2, 3), (2, 2), (1, 2)]
        compacted = normalized
        for head_count, tail_count in candidate_sizes:
            head = lines[:head_count]
            tail = lines[-tail_count:] if tail_count else []
            omitted = max(0, len(lines) - len(head) - len(tail))
            marker = f"... [{omitted} middle context lines omitted] ..."
            candidate = "\n".join([*head, marker, *tail])
            if len(candidate) <= max_chars:
                compacted = candidate
                break
        else:
            head = [lines[0]]
            tail = lines[-2:] if len(lines) >= 2 else lines[-1:]
            omitted = max(0, len(lines) - len(head) - len(tail))
            marker = f"... [{omitted} middle context lines omitted] ..."
            head_text = head[0]
            available_tail_chars = max(20, max_chars - len(marker) - len(head_text) - 2)
            tail_text = "\n".join(tail)
            if len(tail_text) > available_tail_chars:
                tail_budget = available_tail_chars
                if len(tail) >= 2:
                    primary_tail = tail[-2]
                    secondary_tail = tail[-1]
                    if len(primary_tail) + 1 >= tail_budget:
                        tail_text = primary_tail[:tail_budget].rstrip()
                    else:
                        secondary_budget = tail_budget - len(primary_tail) - 1
                        if len(secondary_tail) > secondary_budget:
                            secondary_tail = secondary_tail[: max(secondary_budget - 3, 0)].rstrip() + "..."
                        tail_text = f"{primary_tail}\n{secondary_tail}"
                else:
                    tail_text = tail[0][:tail_budget].rstrip()
            compacted = "\n".join([head_text, marker, tail_text])
            if len(compacted) > max_chars:
                compacted = compacted[: max_chars - 3].rstrip() + "..."
        summary = (
            f"Runtime context compacted from {len(lines)} lines to preserve the opening and latest details."
        )
        return compacted, summary


__all__ = ["KVCachePolicy"]