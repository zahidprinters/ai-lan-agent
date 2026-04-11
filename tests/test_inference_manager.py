from __future__ import annotations

from pathlib import Path

import pytest

from core.inference.engine import InferenceManager, InferenceRequest
from core.inference.model_router import ReasoningModelRouter
from core.inference.residency import ResidencyMonitor, ResidencySnapshot


class _StubRuntime:
    def __call__(self, prompt: str, **_: object) -> dict[str, object]:
        return {"choices": [{"text": '{"mode":"reply","response":"from stub"}'}]}


class _StreamingActionRuntime:
    def __call__(self, prompt: str, **kwargs: object):
        _ = prompt
        if kwargs.get("stream"):
            return iter(
                [
                    {"choices": [{"text": '{"mode":"action","plan":["a","b","c"],'}]},
                    {"choices": [{"text": '"thought":"search","action":"web.search",'}]},
                    {"choices": [{"text": '"args":{"query":"roadmap"},"safety_level":"low"}'}]},
                ]
            )
        return {"choices": [{"text": ""}]}


class _HighPressureMonitor(ResidencyMonitor):
    def sample(self) -> ResidencySnapshot:
        return ResidencySnapshot(
            resident_enabled=True,
            host_ram_percent=92.0,
            unload_ram_pct=85.0,
            pressure_high=True,
            reason=None,
        )


@pytest.mark.unit
def test_inference_manager_routes_simple_tasks_to_simple_model(tmp_path: Path) -> None:
    simple_model = tmp_path / "simple.gguf"
    complex_model = tmp_path / "complex.gguf"
    simple_model.write_text("stub", encoding="utf-8")
    complex_model.write_text("stub", encoding="utf-8")

    router = ReasoningModelRouter(
        router_enabled=True,
        simple_model_path=simple_model,
        complex_model_path=complex_model,
    )

    selection = router.select_model(task_complexity="simple")

    assert selection.model_path == simple_model
    assert selection.selection_reason == "simple_route"


@pytest.mark.unit
def test_model_router_prefers_nonresident_simple_route_under_pressure(tmp_path: Path) -> None:
    simple_model = tmp_path / "simple.gguf"
    complex_model = tmp_path / "complex.gguf"
    simple_model.write_text("stub", encoding="utf-8")
    complex_model.write_text("stub", encoding="utf-8")

    router = ReasoningModelRouter(
        router_enabled=True,
        resident_enabled=True,
        simple_model_path=simple_model,
        complex_model_path=complex_model,
    )

    plan = router.build_plan(task_complexity="complex", pressure_high=True)

    assert plan.primary.model_path == simple_model
    assert plan.primary.selection_reason == "pressure_simple_route"
    assert plan.primary.resident_enabled is False
    assert plan.candidates[1].model_path is not None


@pytest.mark.unit
def test_inference_manager_falls_back_to_secondary_model_when_primary_missing(tmp_path: Path) -> None:
    simple_model = tmp_path / "simple.gguf"
    simple_model.write_text("stub", encoding="utf-8")
    missing_complex_model = tmp_path / "missing-complex.gguf"

    router = ReasoningModelRouter(
        router_enabled=True,
        resident_enabled=False,
        simple_model_path=simple_model,
        complex_model_path=missing_complex_model,
    )
    manager = InferenceManager(router=router, telemetry_enabled=False)

    build_calls: list[Path] = []

    def fake_build_runtime(*, model_path: Path, request: InferenceRequest) -> _StubRuntime:
        _ = request
        build_calls.append(model_path)
        return _StubRuntime()

    manager._build_runtime = fake_build_runtime  # type: ignore[method-assign]

    result = manager.generate(InferenceRequest(prompt="hello", task_complexity="complex"))

    assert result.text == '{"mode":"reply","response":"from stub"}'
    assert result.model_path == str(simple_model)
    assert result.metadata["selection_reason"] == "complex_route_fallback_1"
    assert result.metadata["routing_fallback_applied"] is True
    assert result.metadata["routing_attempts"][0]["fallback_reason"] == "llama_model_missing"
    assert build_calls == [simple_model]


@pytest.mark.unit
def test_inference_manager_returns_high_pressure_fallback(tmp_path: Path) -> None:
    model_path = tmp_path / "resident.gguf"
    model_path.write_text("stub", encoding="utf-8")
    router = ReasoningModelRouter(explicit_model_path=model_path, resident_enabled=True)
    manager = InferenceManager(
        router=router,
        residency_monitor=_HighPressureMonitor(),
        telemetry_enabled=False,
    )

    result = manager.generate(InferenceRequest(prompt="hello"))

    assert result.text == ""
    assert result.fallback_reason == "llama_residency_unloaded_high_pressure"
    assert result.metadata["effective_backend"] == "classic"


@pytest.mark.unit
def test_inference_manager_reuses_loaded_runtime_when_resident(tmp_path: Path) -> None:
    model_path = tmp_path / "resident.gguf"
    model_path.write_text("stub", encoding="utf-8")
    router = ReasoningModelRouter(explicit_model_path=model_path, resident_enabled=True)
    manager = InferenceManager(router=router, telemetry_enabled=False)

    build_calls: list[Path] = []

    def fake_build_runtime(*, model_path: Path, request: InferenceRequest) -> _StubRuntime:
        build_calls.append(model_path)
        return _StubRuntime()

    manager._build_runtime = fake_build_runtime  # type: ignore[method-assign]

    first = manager.generate(InferenceRequest(prompt="hello"))
    second = manager.generate(InferenceRequest(prompt="hello again"))

    assert first.text
    assert second.text
    assert build_calls == [model_path]


@pytest.mark.unit
def test_inference_manager_stream_intercepts_action_payload(tmp_path: Path) -> None:
    model_path = tmp_path / "stream.gguf"
    model_path.write_text("stub", encoding="utf-8")
    router = ReasoningModelRouter(explicit_model_path=model_path, resident_enabled=False)
    manager = InferenceManager(router=router, telemetry_enabled=False)
    manager._build_runtime = lambda **_: _StreamingActionRuntime()  # type: ignore[method-assign]

    result = manager.generate(InferenceRequest(prompt="hello"))

    assert result.text.startswith('{"mode":"action"')
    assert result.metadata["stream_intercepted"] is True


class _StreamingTextActionRuntime:
    def __call__(self, prompt: str, **kwargs: object):
        _ = prompt
        if kwargs.get("stream"):
            return iter(
                [
                    {"choices": [{"text": "Thought: Search docs\n"}]},
                    {"choices": [{"text": "Action: web.search\n"}]},
                    {"choices": [{"text": 'Args: {"query":"ai lan roadmap"}\nSafety: low'}]},
                ]
            )
        return {"choices": [{"text": ""}]}


@pytest.mark.unit
def test_inference_manager_extracts_text_trigger_payload(tmp_path: Path) -> None:
    model_path = tmp_path / "stream-text.gguf"
    model_path.write_text("stub", encoding="utf-8")
    router = ReasoningModelRouter(explicit_model_path=model_path, resident_enabled=False)
    manager = InferenceManager(router=router, telemetry_enabled=False)
    manager._build_runtime = lambda **_: _StreamingTextActionRuntime()  # type: ignore[method-assign]

    result = manager.generate(InferenceRequest(prompt="hello"))

    assert result.metadata["stream_intercepted"] is True
    assert result.metadata["stream_trigger_mode"] == "text_action"
    payload = result.metadata["stream_trigger_payload"]
    assert isinstance(payload, dict)
    assert payload["action"] == "web.search"