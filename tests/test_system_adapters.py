from __future__ import annotations

import subprocess

from tools.system.clipboard import read_clipboard
from tools.system.files import execute_shell


def test_read_clipboard_returns_text(monkeypatch) -> None:
    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            ["powershell"],
            0,
            stdout="hello clipboard\r\n",
            stderr="",
        )

    monkeypatch.setattr("tools.system.clipboard.subprocess.run", fake_run)

    result = read_clipboard()

    assert result == "hello clipboard\n"


def test_read_clipboard_timeout_returns_unavailable(monkeypatch) -> None:
    def fake_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["powershell"], timeout=5)

    monkeypatch.setattr("tools.system.clipboard.subprocess.run", fake_run)

    result = read_clipboard()

    assert result.startswith("unavailable:")
    assert "timed out" in result


def test_execute_shell_blocks_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("AI_LAN_SHELL_ALLOW", raising=False)

    result = execute_shell("Get-Location")

    assert result["status"] == "blocked_policy"
    assert "disabled" in str(result["detail"]).lower()


def test_execute_shell_blocks_when_not_allowlisted(monkeypatch) -> None:
    monkeypatch.setenv("AI_LAN_SHELL_ALLOW", "1")
    monkeypatch.setenv("AI_LAN_SHELL_ALLOWED_COMMANDS", "Get-Location")

    result = execute_shell("Get-ChildItem")

    assert result["status"] == "blocked_policy"
    assert result["command_head"] == "get-childitem"


def test_execute_shell_runs_allowlisted_command(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = kwargs
        command = args[0]
        assert command == ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Location"]
        return subprocess.CompletedProcess(command, 0, stdout="D:\\dextop\\tempn\r\n", stderr="")

    monkeypatch.setenv("AI_LAN_SHELL_ALLOW", "1")
    monkeypatch.setenv("AI_LAN_SHELL_ALLOWED_COMMANDS", "Get-Location")
    monkeypatch.setattr("tools.system.files.subprocess.run", fake_run)

    result = execute_shell("Get-Location")

    assert result["status"] == "ok"
    assert result["returncode"] == 0
    assert "D:\\dextop\\tempn" in str(result["stdout"])
