from __future__ import annotations

"""Voice chat runtime entrypoint.

This module provides a voice-enabled variant of the CLI chat loop. It keeps
the same `ChatSession` core behavior and only changes input/output surfaces.
"""

from training.config import load_config
from runtime.chat_interface import ChatSession, _close_session

try:
    from tools.perception.audio import OfflineSpeechListener, Speaker
except Exception:
    OfflineSpeechListener = None
    Speaker = None


def run_voice_chat_cli() -> int:
    config = load_config()
    session = ChatSession()

    listener = OfflineSpeechListener() if (config.stt_enabled and OfflineSpeechListener) else None
    speaker = Speaker() if (config.tts_enabled and Speaker) else None

    print("AI Lan Voice Chat (offline-first)")
    print("Type /quit to exit. If STT is disabled or unavailable, typed input is used.")

    try:
        while True:
            try:
                if listener is not None:
                    user_input = listener.listen_once(duration_sec=6)
                    if not user_input:
                        user_input = input("you> ").strip()
                    else:
                        print(f"you> {user_input}")
                else:
                    user_input = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting voice chat.")
                return 0

            if user_input in {"/quit", "/exit"}:
                print("Exiting voice chat.")
                return 0

            reply = session.handle_message(user_input)
            print("ai> " + reply.replace("\n", "\nai> "))

            if speaker is not None and reply.strip():
                try:
                    speaker.speak(reply)
                except Exception:
                    # Voice output failure should not break chat loop.
                    pass
    finally:
        _close_session(session)


__all__ = ["run_voice_chat_cli"]
