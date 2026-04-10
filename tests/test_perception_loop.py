from __future__ import annotations

import time

import pytest

from runtime.perception_loop import PerceptionLoop


@pytest.mark.unit
def test_perception_collect_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "runtime.perception_loop.capture_screen_text", lambda: "Inbox 14 unread Build failed"
    )
    loop = PerceptionLoop(interval_sec=1)
    snapshot = loop.collect_once()

    assert snapshot.source == "screen_ocr"
    assert "Inbox" in snapshot.summary
    assert loop.last_snapshot is not None


@pytest.mark.unit
def test_perception_background_start_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("runtime.perception_loop.capture_screen_text", lambda: "hello")

    received: list[str] = []

    def on_snapshot(snapshot) -> None:  # type: ignore[no-untyped-def]
        received.append(snapshot.summary)

    loop = PerceptionLoop(interval_sec=1, on_snapshot=on_snapshot)
    loop.start()
    time.sleep(0.2)
    loop.stop()

    assert loop.is_running is False
    assert received, "Expected at least one snapshot callback"
