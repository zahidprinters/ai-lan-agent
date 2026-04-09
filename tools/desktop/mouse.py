"""Desktop mouse adapter."""

from __future__ import annotations

from debug_utils import sentinel


@sentinel
def move_mouse(x: int, y: int) -> bool:
    """Moves mouse to coordinate (x, y)."""
    print(f"[DesktopMouse] Plot: {x}, {y}")
    return True


__all__ = ["move_mouse"]
