from __future__ import annotations

"""Prompt templates for the ReAct agent."""

from typing import Any

from core.inference.context_manager import compact_prompt_context

from agents.react.tool_schema import format_model_tool_schema

SYSTEM_PROMPT = (
    "You are AI Lan, a helpful local reasoning assistant. "
    "You can engage in natural conversation, answer questions, and execute tool actions. "
    "Be conversational and friendly. When users ask general questions, provide helpful replies. "
    "When they request actions (search, list files, open apps, etc.), execute them safely. "
    "Think step-by-step, explain your reasoning, and act minimally."
)
OUTPUT_RULES = (
    'Return one JSON object only. Always include a "plan" array with 2-5 short steps explaining your reasoning. '
    'For replies: {"mode":"reply","plan":["step1","step2"],"response":"..."}. '
    'For actions: {"mode":"action","plan":["step1","step2"],"thought":"...","action":"...","args":{...},"safety_level":"low|medium|high"}. '
    'Make responses conversational and natural. Explain what you are doing.'
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
    plan_requirements: list[str] | None = None,
) -> str:
    compacted = compact_prompt_context(
        runtime_context=runtime_context,
        recent_turns=recent_turns,
        recent_thoughts=recent_thoughts,
        recent_observations=recent_observations,
    )
    context_text = compacted.runtime_context_text

    tools_text = format_model_tool_schema(tool_names)
    thoughts_text = "\n".join(f"- {thought}" for thought in compacted.recent_thoughts) or "(none)"
    observations_text = (
        "\n".join(f"- {item}" for item in compacted.recent_observations) or "(none)"
    )
    plan_text = "\n".join(f"- {step}" for step in (plan_requirements or [])) or "(none)"

    sections = [
        SYSTEM_PROMPT,
        "For general questions or conversation: reply with a helpful, natural response.",
        "For action requests: decide if a tool is needed and execute safely.",
        "Use the tool schema and recent context to decide whether to reply or act.",
        "Follow the mandatory plan outline to explain your reasoning.",
        "Prefer memory.search and context.build for knowledge within the project.",
        "Prefer web.search for current external information.",
        "Use only tools marked as allowed in the schema.",
        "Be conversational and friendly - avoid robotic responses.",
        _format_block("Available tools:", tools_text),
        _format_block("Plan quality requirements:", plan_text),
        _format_block("Recent turns:", _format_turns(compacted.recent_turns)),
        _format_block("Recent thoughts:", thoughts_text),
        _format_block("Recent observations:", observations_text),
        _format_block("Compacted summaries:", "\n".join(f"- {item}" for item in compacted.summary_blocks)),
        _format_block("Runtime context:", context_text),
        OUTPUT_RULES,
        _format_block("Message:", message.strip()),
    ]
    return "\n\n".join(section for section in sections if section.strip())


__all__ = ["OUTPUT_RULES", "SYSTEM_PROMPT", "build_react_prompt"]
