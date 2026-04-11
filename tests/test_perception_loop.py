from __future__ import annotations

import time

import pytest

from runtime.perception_loop import PerceptionLoop


@pytest.mark.unit
def test_perception_collect_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "runtime.perception_loop.capture_vision_sample",
        lambda **_: {
            "text": "Inbox 14 unread Build failed",
            "filtered_text": "Inbox unread Build failed",
            "source": "screen_ocr",
            "average_confidence": 87.5,
            "sample_count": 1,
        },
    )
    loop = PerceptionLoop(interval_sec=1)
    snapshot = loop.collect_once()

    assert snapshot.source == "screen_ocr"
    assert "Inbox" in snapshot.summary
    assert snapshot.average_confidence == 87.5
    assert loop.last_snapshot is not None


@pytest.mark.unit
def test_perception_background_start_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "runtime.perception_loop.capture_vision_sample",
        lambda **_: {"text": "hello", "filtered_text": "hello", "sample_count": 1},
    )

    received: list[str] = []

    def on_snapshot(snapshot) -> None:  # type: ignore[no-untyped-def]
        received.append(snapshot.summary)

    loop = PerceptionLoop(interval_sec=1, on_snapshot=on_snapshot)
    loop.start()
    time.sleep(0.2)
    loop.stop()

    assert loop.is_running is False
    assert received, "Expected at least one snapshot callback"


@pytest.mark.unit
def test_perception_adaptive_interval_backs_off_when_screen_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "runtime.perception_loop.capture_vision_sample",
        lambda **_: {"text": "unchanged screen summary", "filtered_text": "", "sample_count": 1},
    )

    loop = PerceptionLoop(interval_sec=2, max_interval_sec=8, adaptive=True)
    first = loop.collect_once()
    second = loop.collect_once()

    assert first.summary == second.summary
    assert loop.current_interval_sec > 2


@pytest.mark.unit
def test_perception_adaptive_interval_resets_on_content_change(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = iter(["screen one", "screen one", "screen two"])
    monkeypatch.setattr(
        "runtime.perception_loop.capture_vision_sample",
        lambda **_: {"text": next(outputs), "filtered_text": "", "sample_count": 1},
    )

    loop = PerceptionLoop(interval_sec=2, max_interval_sec=8, adaptive=True)
    loop.collect_once()
    loop.collect_once()
    assert loop.current_interval_sec > 2

    loop.collect_once()
    assert loop.current_interval_sec == 2


@pytest.mark.unit
def test_perception_collect_once_uses_bounded_sample_count(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def fake_capture(**kwargs: object) -> dict[str, object]:
        seen.append(int(kwargs.get("max_samples", 0)))
        return {
            "text": "status panel visible",
            "filtered_text": "status panel visible",
            "sample_count": int(kwargs.get("max_samples", 1)),
        }

    monkeypatch.setattr("runtime.perception_loop.capture_vision_sample", fake_capture)

    loop = PerceptionLoop(interval_sec=1, max_samples_per_tick=3)
    snapshot = loop.collect_once()

    assert seen == [3]
    assert snapshot.sample_count == 3
