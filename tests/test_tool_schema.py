from __future__ import annotations

import pytest

from agents.react.prompt import build_react_prompt
from agents.react.tool_schema import build_model_tool_schema, format_model_tool_schema


@pytest.mark.unit
def test_build_model_tool_schema_includes_confirmation_and_risk() -> None:
    schema = build_model_tool_schema(["pc.open_app", "web.search"])
    payload = {item.name: item for item in schema}

    assert payload["pc.open_app"].confirmation_required is True
    assert payload["pc.open_app"].risk == "medium"
    assert payload["web.search"].allowed is True


@pytest.mark.unit
def test_format_model_tool_schema_renders_structured_fields() -> None:
    rendered = format_model_tool_schema(["memory.search"])

    assert "memory.search" in rendered
    assert "required_args: query" in rendered
    assert "confirmation_required: no" in rendered


@pytest.mark.unit
def test_build_react_prompt_uses_structured_tool_schema() -> None:
    prompt = build_react_prompt(
        message="search for current status",
        runtime_context={"assembled_context": "runtime summary"},
        tool_names=["web.search"],
    )

    assert "description: Search the web for current external information." in prompt
    assert "allowed: yes" in prompt
    assert "Use only tools marked as allowed in the schema." in prompt