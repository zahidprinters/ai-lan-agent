"""Desktop keyboard adapter."""

from __future__ import annotations

from debug_utils import sentinel


@sentinel
def type_text(text: str) -> bool:
    """Simulates keyboard typing."""
    print(f"[DesktopKeyboard] Type: {text}")
    return True


__all__ = ["type_text"]
