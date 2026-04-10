from __future__ import annotations

import pytest

from runtime.voice_chat_interface import run_voice_chat_cli
from tools.perception.audio.stt import OfflineSpeechListener


@pytest.mark.unit
def test_stt_listener_uses_env_text_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_VOICE_TEXT_INPUT", "hello from voice")
    listener = OfflineSpeechListener()
    assert listener.listen_once() == "hello from voice"


@pytest.mark.unit
def test_voice_chat_cli_falls_back_to_typed_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeConfig:
        stt_enabled = False
        tts_enabled = False

    class FakeSession:
        def handle_message(self, message: str) -> str:
            return f"echo:{message}"

    inputs = iter(["hello", "/quit"])

    monkeypatch.setattr("runtime.voice_chat_interface.load_config", lambda: FakeConfig())
    monkeypatch.setattr("runtime.voice_chat_interface.ChatSession", lambda: FakeSession())
    monkeypatch.setattr("builtins.input", lambda _='': next(inputs))

    code = run_voice_chat_cli()
    out = capsys.readouterr().out

    assert code == 0
    assert "AI Lan Voice Chat" in out
    assert "echo:hello" in out


@pytest.mark.unit
def test_voice_chat_cli_uses_stt_when_available(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeConfig:
        stt_enabled = True
        tts_enabled = False

    class FakeSession:
        def handle_message(self, message: str) -> str:
            return f"ok:{message}"

    class FakeListener:
        def __init__(self) -> None:
            self._items = iter(["voice command", "/quit"])

        def listen_once(self, duration_sec: int = 6) -> str:
            _ = duration_sec
            return next(self._items)

    monkeypatch.setattr("runtime.voice_chat_interface.load_config", lambda: FakeConfig())
    monkeypatch.setattr("runtime.voice_chat_interface.ChatSession", lambda: FakeSession())
    monkeypatch.setattr("runtime.voice_chat_interface.OfflineSpeechListener", lambda: FakeListener())

    code = run_voice_chat_cli()
    out = capsys.readouterr().out

    assert code == 0
    assert "voice command" in out
    assert "ok:voice command" in out
