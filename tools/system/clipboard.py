"""System clipboard adapter."""

from __future__ import annotations

from debug_utils import sentinel


@sentinel
def read_clipboard() -> str:
    """Returns a deterministic placeholder clipboard value until a safe adapter is added."""
    print("[SystemClipboard] Read Clipboard")
    return "STUB: Clipboard read not yet connected to the system clipboard."


__all__ = ["read_clipboard"]
