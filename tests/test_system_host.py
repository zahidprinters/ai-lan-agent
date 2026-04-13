from __future__ import annotations

import subprocess

import pytest

from tools.system.host import list_running_apps, open_app


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


def test_open_app_blocks_non_allowlisted_app() -> None:
    result = open_app("totally-unknown-app")

    assert result["status"] == "blocked_policy"
    assert "allowlist" in str(result["detail"]).lower()


def test_open_app_launches_allowlisted_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched: dict[str, object] = {}

    class FakeProcess:
        pid = 4321

    def fake_popen(command: list[str], **_: object) -> FakeProcess:
        launched["command"] = command
        return FakeProcess()

    monkeypatch.setattr("tools.system.host.subprocess.Popen", fake_popen)

    result = open_app("notepad")

    assert result["status"] == "ok"
    assert result["pid"] == 4321
    assert launched["command"] == ["notepad.exe"]


def test_open_app_uses_env_allowlist_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched: dict[str, object] = {}

    class FakeProcess:
        pid = 999

    def fake_popen(command: list[str], **_: object) -> FakeProcess:
        launched["command"] = command
        return FakeProcess()

    monkeypatch.setenv("AI_LAN_ALLOWED_APPS", "mynotes=custom-notes.exe")
    monkeypatch.setattr("tools.system.host.subprocess.Popen", fake_popen)

    result = open_app("mynotes")

    assert result["status"] == "ok"
    assert launched["command"] == ["custom-notes.exe"]
