from __future__ import annotations

from dataclasses import replace

import pytest

from agents.react.controller import NeuralActionController
from agents.react.planner import build_plan_requirements, validate_or_repair_plan
from core.inference.context_manager import compact_prompt_context
from core.inference.engine import reset_default_inference_manager
from core.inference.local_reasoning import (
    generate_structured_response,
    generate_structured_response_result,
)


@pytest.fixture(autouse=True)
def _reset_inference_manager() -> None:
    reset_default_inference_manager()


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
    monkeypatch.delenv("AI_LAN_MODEL_ROUTER_SIMPLE_MODEL_PATH", raising=False)
    monkeypatch.delenv("AI_LAN_MODEL_ROUTER_COMPLEX_MODEL_PATH", raising=False)
    monkeypatch.delenv("AI_LAN_LLAMACPP_MODEL_PROFILE", raising=False)

    result = generate_structured_response_result(prompt="hello")

    assert result.text == ""
    assert result.fallback_reason == "llama_model_missing"


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
    assert turn.metadata is not None
    assert turn.metadata["effective_backend"] == "llama_cpp"


@pytest.mark.unit
def test_local_reasoning_result_includes_manager_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeManager:
        def generate(self, request: object):
            return type(
                "R",
                (),
                {
                    "text": '{"mode":"reply","response":"local"}',
                    "fallback_reason": None,
                    "metadata": {"effective_backend": "llama_cpp", "selection_reason": "simple_route"},
                },
            )()

    monkeypatch.setattr("core.inference.local_reasoning.get_default_inference_manager", lambda: _FakeManager())

    result = generate_structured_response_result(prompt="hello", task_complexity="simple")

    assert result.text
    assert result.fallback_reason is None
    assert result.metadata is not None
    assert result.metadata["selection_reason"] == "simple_route"


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
        observe_action=lambda turn: seen_payloads.append(turn.action_payload or {}) or "memory hit observed",
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
        observe_action=lambda turn: observed.append(turn.action_payload or {}) or "same observation",
    )

    assert len(turns) == 1
    assert observed


@pytest.mark.unit
def test_mandatory_plan_has_three_to_five_steps() -> None:
    simple_plan = build_plan_requirements(message="search roadmap", task_complexity="simple")
    complex_plan = build_plan_requirements(
        message="analyze the latest safety policy state", task_complexity="complex"
    )

    assert 3 <= simple_plan.min_steps <= simple_plan.max_steps <= 5
    assert 3 <= complex_plan.min_steps <= complex_plan.max_steps <= 5
    assert len(simple_plan.quality_checks) >= 4
    assert len(complex_plan.quality_checks) >= 4


@pytest.mark.unit
def test_plan_validation_repairs_refusal_shape_for_blocked_action() -> None:
    result = validate_or_repair_plan(
        candidate_steps=["search", "run tool", "reply"],
        message="run shell command",
        task_complexity="complex",
        action_payload={
            "thought": "run shell",
            "action": "pc.execute_shell",
            "args": {"command": "dir"},
            "safety_level": "high",
        },
    )

    assert result.valid is False
    assert any("refus" in step.lower() or "policy" in step.lower() for step in result.steps)


@pytest.mark.unit
def test_compact_prompt_context_summarizes_older_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_KV_CACHE_MAX_TURNS", "3")
    compacted = compact_prompt_context(
        runtime_context={"assembled_context": "current context"},
        recent_turns=[
            {"role": "user", "message": f"turn-{index}"}
            for index in range(5)
        ],
        recent_thoughts=[f"thought-{index}" for index in range(5)],
        recent_observations=[f"obs-{index}" for index in range(5)],
    )

    assert compacted.compacted is True
    assert len(compacted.recent_turns) == 3
    assert any("Compacted earlier turns" in item for item in compacted.summary_blocks)
    assert any("roles:" in item for item in compacted.summary_blocks)


@pytest.mark.unit
def test_compact_prompt_context_preserves_runtime_context_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_RUNTIME_CONTEXT_MAX_CHARS", "140")
    long_context = "\n".join(
        [
            "Perception Context:",
            "Inbox visible with several unread items.",
            "Calendar panel open with upcoming meetings.",
            "Memory hits mention policy confirmation.",
            "Workspace docs include 4.5A status.",
            "Latest observation says tool execution succeeded.",
            "Recent reply summarized the fallback route.",
        ]
    )

    compacted = compact_prompt_context(
        runtime_context={"assembled_context": long_context},
        recent_turns=[],
        recent_thoughts=[],
        recent_observations=[],
    )

    assert compacted.runtime_context_text.startswith("Perception Context:")
    assert "Latest observation says tool execution succeeded." in compacted.runtime_context_text
    assert "middle context lines omitted" in compacted.runtime_context_text
    assert any(
        "Runtime context compacted" in item for item in compacted.summary_blocks
    )


@pytest.mark.unit
def test_controller_parses_plan_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(reasoning_backend="classic")
    monkeypatch.setattr(
        "agents.react.controller.generate_text",
        lambda *_, **__: '{"mode":"reply","plan":["one","two","three"],"response":"ok"}',
    )

    turn = controller.plan(message="hello")

    assert turn is not None
    assert turn.metadata is not None
    assert 3 <= len(turn.metadata["plan_steps"]) <= 5
    assert "plan_validation" in turn.metadata
    assert turn.metadata["plan_validation"]["source"] in {"model_validated", "repaired"}


@pytest.mark.unit
def test_controller_supports_text_action_trigger_format(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(reasoning_backend="classic")
    monkeypatch.setattr(
        "agents.react.controller.generate_text",
        lambda *_, **__: 'Thought: Search docs\nAction: web.search\nArgs: {"query":"ai lan"}\nSafety: low',
    )

    turn = controller.plan(message="search ai lan")

    assert turn is not None
    assert turn.mode == "action"
    assert turn.source == "model_stream_trigger"
    assert turn.action_payload is not None
    assert turn.action_payload["action"] == "web.search"


@pytest.mark.unit
def test_controller_blocks_misaligned_stream_trigger_before_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(enabled=True, reasoning_backend="classic")
    streamed_turn = controller._parse_output(
        'Thought: Launch app\nAction: android.launch_app\nArgs: {"package_name":"com.example.app"}\nSafety: medium'
    )
    assert streamed_turn is not None
    assert streamed_turn.mode == "action"
    assert streamed_turn.action_payload is not None

    streamed_turn = replace(
        streamed_turn,
        metadata={
            "stream_trigger_mode": "text_action",
            "plan_validation": {"source": "model_validated"},
            "plan_steps": [
                "Write a direct response without using tools.",
                "Polish wording for clarity.",
                "Send the final answer.",
            ],
        },
    )
    monkeypatch.setattr(controller, "plan", lambda **_: streamed_turn)

    observed: list[dict[str, object]] = []
    turns = controller.plan_iterative(
        message="launch app",
        observe_action=lambda turn: observed.append(turn.action_payload or {}) or "should not run",
    )

    assert observed == []
    assert len(turns) == 1
    assert turns[0].mode == "reply"
    assert turns[0].source == "runtime_guard"
    assert turns[0].metadata is not None
    assert turns[0].metadata["runtime_guard"]["reason"] in {
        "runtime_stream_trigger_plan_mismatch",
        "runtime_risk_confirmation_path_missing",
    }


@pytest.mark.unit
def test_controller_allows_aligned_stream_trigger_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = NeuralActionController(enabled=True, reasoning_backend="classic")
    streamed_turn = controller._parse_output(
        'Thought: Search memory\nAction: memory.search\nArgs: {"query":"policy"}\nSafety: low'
    )
    assert streamed_turn is not None
    assert streamed_turn.mode == "action"
    assert streamed_turn.action_payload is not None

    streamed_turn = replace(
        streamed_turn,
        metadata={
            "stream_trigger_mode": "text_action",
            "plan_validation": {"source": "model_validated"},
            "plan_steps": [
                "Understand the policy question.",
                "Use memory.search to gather relevant records.",
                "Verify the retrieved context before replying.",
            ],
        },
    )
    reply_turn = controller._parse_output('{"mode":"reply","response":"done"}')
    assert reply_turn is not None
    monkeypatch.setattr(controller, "plan", lambda **kwargs: streamed_turn if not (kwargs.get("recent_observations") or []) else reply_turn)

    observed: list[dict[str, object]] = []
    turns = controller.plan_iterative(
        message="search memory",
        observe_action=lambda turn: observed.append(turn.action_payload or {}) or "observation",
    )

    assert observed
    assert len(turns) == 2
    assert turns[0].mode == "action"
    assert turns[0].metadata is not None
    assert turns[0].metadata["runtime_guard"]["allowed"] is True
    assert turns[0].metadata["execution_contract"]["guard_allowed"] is True
