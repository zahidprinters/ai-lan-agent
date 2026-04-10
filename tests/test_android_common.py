from __future__ import annotations

import subprocess

import pytest

from tools.android._common import run_adb_command


def test_run_adb_command_timeout_returns_text_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_ANDROID_ADB_TIMEOUT_SECONDS", "9")

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["adb", "devices"], timeout=9)

    monkeypatch.setattr("tools.android._common.subprocess.run", timeout_run)

    result = run_adb_command(["adb", "devices"], text=True)

    assert result is not None
    assert result.returncode == 124
    assert isinstance(result.stderr, str)
    assert "timed out" in result.stderr
    assert "9s" in result.stderr


def test_run_adb_command_timeout_returns_binary_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_ANDROID_ADB_TIMEOUT_SECONDS", "7")

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["adb", "exec-out"], timeout=7)

    monkeypatch.setattr("tools.android._common.subprocess.run", timeout_run)

    result = run_adb_command(["adb", "exec-out", "screencap", "-p"], text=False)

    assert result is not None
    assert result.returncode == 124
    assert isinstance(result.stderr, bytes)
    assert b"timed out" in result.stderr
    assert b"7s" in result.stderr


def test_run_adb_command_invalid_timeout_env_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_ANDROID_ADB_TIMEOUT_SECONDS", "not-a-number")

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["adb"], timeout=15)

    monkeypatch.setattr("tools.android._common.subprocess.run", timeout_run)

    result = run_adb_command(["adb", "devices"], text=True)

    assert result is not None
    assert result.returncode == 124
    assert "15s" in result.stderr
