"""System clipboard adapter."""

from __future__ import annotations

import os
import subprocess

from debug_utils import sentinel


def _get_clipboard_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_CLIPBOARD_TIMEOUT_SECONDS", "5").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 5
    return max(1, min(timeout, 30))


def _get_clipboard_max_chars() -> int:
    raw_value = os.getenv("AI_LAN_CLIPBOARD_MAX_CHARS", "4000").strip()
    try:
        max_chars = int(raw_value)
    except ValueError:
        return 4000
    return max(64, min(max_chars, 20000))


@sentinel
def read_clipboard() -> str:
    """Read clipboard text through a bounded PowerShell call."""
    timeout_seconds = _get_clipboard_timeout_seconds()
    max_chars = _get_clipboard_max_chars()
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "Get-Clipboard -Raw",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return f"unavailable: clipboard read timed out after {timeout_seconds}s"
    except FileNotFoundError:
        return "unavailable: powershell not found"

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "clipboard read failed"
        return f"unavailable: {detail}"

    clipboard_text = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    if not clipboard_text:
        return ""
    if len(clipboard_text) > max_chars:
        return clipboard_text[:max_chars] + "\n...[truncated]"
    return clipboard_text


__all__ = ["read_clipboard"]
