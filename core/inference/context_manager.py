from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.inference.kv_cache_manager import KVCachePolicy


@dataclass(frozen=True)
class CompactedPromptContext:
    recent_turns: list[dict[str, str]]
    recent_thoughts: list[str]
    recent_observations: list[str]
    runtime_context_text: str
    summary_blocks: list[str]
    compacted: bool


def _compact_turns(turns: list[dict[str, str]], policy: KVCachePolicy) -> tuple[list[dict[str, str]], str]:
    if not policy.should_compact(len(turns)):
        return list(turns), ""
    older = turns[: -policy.max_turns]
    recent = turns[-policy.max_turns :]
    role_counts: dict[str, int] = {}
    older_lines: list[str] = []
    for item in older:
        role = str(item.get("role", "unknown")).strip().lower() or "unknown"
        role_counts[role] = role_counts.get(role, 0) + 1
        older_lines.append(f"{role}: {item.get('message', '')}")
    role_summary = ", ".join(
        f"{role}={count}" for role, count in sorted(role_counts.items())
    )
    compacted = policy.summarize_lines(older_lines, prefix="Compacted earlier turns")
    if compacted and role_summary:
        compacted = f"{compacted}; roles: {role_summary}"
    return recent, compacted


def _compact_items(items: list[str], policy: KVCachePolicy, *, prefix: str) -> tuple[list[str], str]:
    if not policy.should_compact(len(items)):
        return list(items), ""
    older = items[: -policy.max_turns]
    recent = items[-policy.max_turns :]
    return recent, policy.summarize_lines(older, prefix=prefix)


def compact_prompt_context(
    *,
    runtime_context: dict[str, Any] | None,
    recent_turns: list[dict[str, str]] | None,
    recent_thoughts: list[str] | None,
    recent_observations: list[str] | None,
    policy: KVCachePolicy | None = None,
) -> CompactedPromptContext:
    resolved_policy = policy or KVCachePolicy.from_env()
    turns = list(recent_turns or [])
    thoughts = list(recent_thoughts or [])
    observations = list(recent_observations or [])

    compacted_turns, turns_summary = _compact_turns(turns, resolved_policy)
    compacted_thoughts, thoughts_summary = _compact_items(
        thoughts, resolved_policy, prefix="Compacted earlier thoughts"
    )
    compacted_observations, observations_summary = _compact_items(
        observations, resolved_policy, prefix="Compacted earlier observations"
    )

    runtime_context_text = ""
    runtime_context_summary = ""
    if isinstance(runtime_context, dict):
        raw_runtime_context_text = str(
            runtime_context.get("assembled_context") or runtime_context.get("context_text") or ""
        )
        runtime_context_text, runtime_context_summary = resolved_policy.compact_runtime_context(
            raw_runtime_context_text
        )

    summary_blocks = [
        block
        for block in (
            turns_summary,
            thoughts_summary,
            observations_summary,
            runtime_context_summary,
        )
        if block.strip()
    ]
    return CompactedPromptContext(
        recent_turns=compacted_turns,
        recent_thoughts=compacted_thoughts,
        recent_observations=compacted_observations,
        runtime_context_text=runtime_context_text,
        summary_blocks=summary_blocks,
        compacted=bool(summary_blocks),
    )


__all__ = ["CompactedPromptContext", "compact_prompt_context"]