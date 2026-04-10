from __future__ import annotations

import pytest

from agents.react.controller import NeuralActionController
from core.inference.local_reasoning import (
    generate_structured_response,
    generate_structured_response_result,
)


@pytest.mark.unit
def test_local_reasoning_returns_empty_without_model_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_LAN_LLAMACPP_MODEL_PATH", raising=False)
    text = generate_structured_response(prompt="hello")
    assert text == ""


@pytest.mark.unit
def test_local_reasoning_result_includes_fallback_reason_when_model_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_LAN_LLAMACPP_MODEL_PATH", raising=False)

    result = generate_structured_response_result(prompt="hello")

    assert result.text == ""
    assert result.fallback_reason == "llama_model_not_configured"


@pytest.mark.unit
def test_controller_llama_backend_falls_back_to_classic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_REASONING_BACKEND", "llama_cpp")
    monkeypatch.setattr(
        "agents.react.controller.generate_structured_response_result",
        lambda **_: type("R", (), {"text": "", "fallback_reason": "llama_runtime_unavailable"})(),
    )
    monkeypatch.setattr(
        "agents.react.controller.generate_text",
        lambda *_, **__: '{"mode":"reply","response":"classic fallback"}',
    )

    controller = NeuralActionController()
    turn = controller.plan(message="hello")

    assert turn is not None
    assert turn.mode == "reply"
    assert turn.reply_text == "classic fallback"
    assert turn.metadata is not None
    assert turn.metadata["fallback_reason"] == "llama_runtime_unavailable"
    assert turn.metadata["effective_backend"] == "classic"


@pytest.mark.unit
def test_controller_llama_backend_parses_model_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_REASONING_BACKEND", "llama_cpp")
    monkeypatch.setattr(
        "agents.react.controller.generate_structured_response_result",
        lambda **_: type(
            "R", (), {"text": '{"mode":"reply","response":"from local brain"}', "fallback_reason": None}
        )(),
    )
    monkeypatch.setattr("agents.react.controller.generate_text", lambda *_, **__: "")

    controller = NeuralActionController()
    turn = controller.plan(message="hello")

    assert turn is not None
    assert turn.mode == "reply"
    assert turn.reply_text == "from local brain"
    assert turn.metadata is None


@pytest.mark.unit
def test_controller_plan_iterative_uses_observations(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(enabled=True)

    def fake_plan(**kwargs: object):
        observations = kwargs.get("recent_observations") or []
        if not observations:
            return controller._parse_output(
                '{"mode":"action","thought":"search memory","action":"memory.search","args":{"query":"typing safety"},"safety_level":"low"}'
            )
        return controller._parse_output('{"mode":"reply","response":"I found the memory guidance."}')

    monkeypatch.setattr(controller, "plan", fake_plan)

    seen_payloads: list[dict[str, object]] = []

    turns = controller.plan_iterative(
        message="check memory",
        observe_action=lambda payload: seen_payloads.append(payload) or "memory hit observed",
    )

    assert len(turns) == 2
    assert turns[0].mode == "action"
    assert turns[1].mode == "reply"
    assert turns[1].reply_text == "I found the memory guidance."
    assert seen_payloads[0]["action"] == "memory.search"


@pytest.mark.unit
def test_controller_plan_iterative_stops_on_repeated_action(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(enabled=True)
    repeated_turn = controller._parse_output(
        '{"mode":"action","thought":"search memory","action":"memory.search","args":{"query":"typing safety"},"safety_level":"low"}'
    )
    assert repeated_turn is not None

    monkeypatch.setattr(controller, "plan", lambda **_: repeated_turn)

    observed: list[dict[str, object]] = []
    turns = controller.plan_iterative(
        message="check memory",
        max_steps=4,
        observe_action=lambda payload: observed.append(payload) or "same observation",
    )

    assert len(turns) == 1
    assert observed
