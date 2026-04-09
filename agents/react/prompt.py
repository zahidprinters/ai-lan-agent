from __future__ import annotations

"""Prompt templates for the ReAct agent."""

from typing import Any

SYSTEM_PROMPT = "You are AI Lan. Think safely, act minimally, and log every tool call."
OUTPUT_RULES = (
    'Return one JSON object only. Use {"mode":"action","thought":"...","action":"...","args":{...},"safety_level":"low"} '
    'or {"mode":"reply","response":"..."}.'
)


def _format_block(title: str, value: str | None) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        text = "(none)"
    return f"{title}\n{text}"


def _format_turns(turns: list[dict[str, str]] | None, *, limit: int = 8) -> str:
    if not turns:
        return "(none)"
    selected = turns[-max(limit, 1) :]
    return "\n".join(
        f"- {turn.get('role', 'unknown')}: {turn.get('message', '')}" for turn in selected
    )


def build_react_prompt(
    *,
    message: str,
    runtime_context: dict[str, Any] | None = None,
    recent_turns: list[dict[str, str]] | None = None,
    recent_thoughts: list[str] | None = None,
    recent_observations: list[str] | None = None,
    tool_names: list[str] | tuple[str, ...] | None = None,
) -> str:
    context_text = ""
    if isinstance(runtime_context, dict):
        context_text = str(
            runtime_context.get("assembled_context") or runtime_context.get("context_text") or ""
        )

    tools_text = ", ".join(sorted(tool_names or [])) if tool_names else "(none)"
    thoughts_text = (
        "\n".join(f"- {thought}" for thought in (recent_thoughts or [])[-8:]) or "(none)"
    )
    observations_text = (
        "\n".join(f"- {item}" for item in (recent_observations or [])[-8:]) or "(none)"
    )

    sections = [
        SYSTEM_PROMPT,
        "Use the tool list and recent context to decide whether to reply or act.",
        "Prefer memory.search and context.build for internal knowledge queries.",
        "Prefer web.search for current external information.",
        "Use only the available tool names.",
        _format_block("Available tools:", tools_text),
        _format_block("Recent turns:", _format_turns(recent_turns)),
        _format_block("Recent thoughts:", thoughts_text),
        _format_block("Recent observations:", observations_text),
        _format_block("Runtime context:", context_text),
        OUTPUT_RULES,
        _format_block("Message:", message.strip()),
    ]
    return "\n\n".join(section for section in sections if section.strip())


__all__ = ["OUTPUT_RULES", "SYSTEM_PROMPT", "build_react_prompt"]
