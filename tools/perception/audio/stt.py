from __future__ import annotations

"""Offline speech-to-text helpers for Phase 4.5 voice interaction."""

import os
from pathlib import Path
from typing import Any

from debug_utils import sentinel


class OfflineSpeechListener:
    """Small Vosk-based listener facade with dependency-safe fallbacks."""

    def __init__(self, model_path: str | Path | None = None, sample_rate: int = 16_000) -> None:
        self.sample_rate = int(sample_rate)
        configured_model = os.getenv("AI_LAN_VOSK_MODEL_PATH", "").strip()
        if model_path is not None:
            self.model_path = Path(model_path)
        elif configured_model:
            self.model_path = Path(configured_model)
        else:
            self.model_path = Path("temp") / "vosk-model"

    @sentinel
    def listen_once(self, duration_sec: int = 6) -> str:
        """Capture a short utterance and return recognized text.

        Returns an empty string when dependencies are unavailable or no speech is
        recognized, allowing callers to gracefully fall back to typed input.
        """
        test_text = os.getenv("AI_LAN_VOICE_TEXT_INPUT", "").strip()
        if test_text:
            return test_text

        if not self.model_path.exists():
            return ""

        try:
            import json
            import pyaudio  # type: ignore[import-untyped]
            from vosk import KaldiRecognizer, Model  # type: ignore[import-untyped]
        except Exception:
            return ""

        try:
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, self.sample_rate)

            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=4096,
            )
            stream.start_stream()

            loops = max(1, int((duration_sec * self.sample_rate) / 4096))
            final_result: dict[str, Any] = {}

            for _ in range(loops):
                data = stream.read(4096, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    parsed = json.loads(recognizer.Result())
                    if isinstance(parsed, dict):
                        final_result = parsed

            partial = json.loads(recognizer.FinalResult())
            if isinstance(partial, dict) and partial.get("text"):
                final_result = partial

            stream.stop_stream()
            stream.close()
            audio.terminate()

            text = str(final_result.get("text", "")).strip()
            return text
        except Exception:
            return ""


__all__ = ["OfflineSpeechListener"]
