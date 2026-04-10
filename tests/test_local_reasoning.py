from __future__ import annotations

import pytest

from agents.react.controller import NeuralActionController
from core.inference.local_reasoning import generate_structured_response


@pytest.mark.unit
def test_local_reasoning_returns_empty_without_model_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_LAN_LLAMACPP_MODEL_PATH", raising=False)
    text = generate_structured_response(prompt="hello")
    assert text == ""


@pytest.mark.unit
def test_controller_llama_backend_falls_back_to_classic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_REASONING_BACKEND", "llama_cpp")
    monkeypatch.setattr("agents.react.controller.generate_structured_response", lambda **_: "")
    monkeypatch.setattr(
        "agents.react.controller.generate_text",
        lambda *_, **__: '{"mode":"reply","response":"classic fallback"}',
    )

    controller = NeuralActionController()
    turn = controller.plan(message="hello")

    assert turn is not None
    assert turn.mode == "reply"
    assert turn.reply_text == "classic fallback"


@pytest.mark.unit
def test_controller_llama_backend_parses_model_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_REASONING_BACKEND", "llama_cpp")
    monkeypatch.setattr(
        "agents.react.controller.generate_structured_response",
        lambda **_: '{"mode":"reply","response":"from local brain"}',
    )
    monkeypatch.setattr("agents.react.controller.generate_text", lambda *_, **__: "")

    controller = NeuralActionController()
    turn = controller.plan(message="hello")

    assert turn is not None
    assert turn.mode == "reply"
    assert turn.reply_text == "from local brain"
