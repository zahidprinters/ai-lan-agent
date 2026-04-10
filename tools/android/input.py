"""Android input adapters."""

from __future__ import annotations

from debug_utils import sentinel

from tools.android._common import (
    adb_base_command,
    allow_side_effects,
    run_adb_command,
    validate_allowed_device,
)


def _validate_coordinates(*values: int) -> dict[str, str] | None:
    if any(value < 0 for value in values):
        return {
            "status": "blocked_policy",
            "detail": "Android input coordinates must be non-negative integers.",
        }
    return None


@sentinel
def tap_screen(x: int, y: int, device_id: str | None = None) -> dict[str, str]:
    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable adb side effects.",
        }

    coordinate_violation = _validate_coordinates(x, y)
    if coordinate_violation is not None:
        return coordinate_violation

    device_violation = validate_allowed_device(device_id)
    if device_violation is not None:
        return device_violation

    command = adb_base_command(device_id) + ["shell", "input", "tap", str(x), str(y)]
    result = run_adb_command(command, text=True)
    if result is None:
        return {"status": "failed", "detail": "adb executable not found"}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "detail": (result.stdout or result.stderr).strip(),
    }


@sentinel
def swipe_screen(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
    device_id: str | None = None,
) -> dict[str, str]:
    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable adb side effects.",
        }

    coordinate_violation = _validate_coordinates(x1, y1, x2, y2)
    if coordinate_violation is not None:
        return coordinate_violation
    if duration_ms < 0:
        return {
            "status": "blocked_policy",
            "detail": "Android swipe duration_ms must be zero or greater.",
        }

    device_violation = validate_allowed_device(device_id)
    if device_violation is not None:
        return device_violation

    command = adb_base_command(device_id) + [
        "shell",
        "input",
        "swipe",
        str(x1),
        str(y1),
        str(x2),
        str(y2),
        str(duration_ms),
    ]
    result = run_adb_command(command, text=True)
    if result is None:
        return {"status": "failed", "detail": "adb executable not found"}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "detail": (result.stdout or result.stderr).strip(),
    }


__all__ = ["tap_screen", "swipe_screen"]
