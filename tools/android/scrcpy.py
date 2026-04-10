"""scrcpy launcher facade for Phase 4 Android mirror/control.

Launches scrcpy to display and optionally control a connected Android device.
Guarded by ``AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS``.
"""

from __future__ import annotations

import shutil
import subprocess

from debug_utils import sentinel

from tools.android._common import allow_side_effects


@sentinel
def start_mirror(
    device_id: str | None = None,
    *,
    max_bitrate: str = "8M",
    max_fps: int = 30,
    no_control: bool = False,
) -> dict[str, str]:
    """Launch scrcpy to mirror the connected Android device screen.

    Returns immediately — scrcpy runs in its own window.

    Args:
        device_id: ADB serial of the target device (omit for the only connected device).
        max_bitrate: Video bitrate budget (e.g. ``"4M"``).
        max_fps: Frame-rate cap.
        no_control: If ``True`` launches in view-only mode (no touch/keyboard forwarding).

    Returns a dict with ``status`` and ``detail`` keys.
    """
    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable scrcpy launch.",
        }

    if not shutil.which("scrcpy"):
        return {
            "status": "failed",
            "detail": (
                "scrcpy not found on PATH.  "
                "Install via: winget install --id Genymobile.scrcpy"
            ),
        }

    cmd = ["scrcpy", f"--video-bit-rate={max_bitrate}", f"--max-fps={max_fps}"]
    if device_id:
        cmd.extend(["--serial", device_id])
    if no_control:
        cmd.append("--no-control")

    try:
        subprocess.Popen(cmd)
        return {"status": "launched", "detail": f"scrcpy started: {' '.join(cmd)}"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


__all__ = ["start_mirror"]
