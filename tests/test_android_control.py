from __future__ import annotations

import pytest
from tools.android_control import capture_screenshot, launch_app, tap_screen


def test_android_actions_blocked_in_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "0")
    launch = launch_app("com.example.app")
    tap = tap_screen(10, 10)
    screenshot = capture_screenshot()

    assert launch["status"] == "blocked_safe_mode"
    assert tap["status"] == "blocked_safe_mode"
    assert screenshot["status"] == "blocked_safe_mode"
