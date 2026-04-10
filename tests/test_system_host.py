from __future__ import annotations

import subprocess

import pytest

from tools.system.host import list_running_apps


def test_list_running_apps_timeout_returns_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS", "6")

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["tasklist"], timeout=6)

    monkeypatch.setattr("tools.system.host.subprocess.run", timeout_run)

    result = list_running_apps()

    assert len(result) == 1
    assert result[0].startswith("unavailable:")
    assert "timed out" in result[0]
    assert "6s" in result[0]


def test_list_running_apps_missing_tasklist_returns_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_tasklist(*_: object, **__: object) -> object:
        raise FileNotFoundError("tasklist")

    monkeypatch.setattr("tools.system.host.subprocess.run", missing_tasklist)

    result = list_running_apps()

    assert result == ["unavailable: tasklist not found"]


def test_list_running_apps_invalid_timeout_env_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS", "invalid")

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["tasklist"], timeout=8)

    monkeypatch.setattr("tools.system.host.subprocess.run", timeout_run)

    result = list_running_apps()

    assert len(result) == 1
    assert "8s" in result[0]
