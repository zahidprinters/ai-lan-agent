"""Android screenshot adapter."""

from __future__ import annotations

from pathlib import Path

from debug_utils import sentinel

from tools.android._common import adb_base_command, allow_side_effects, run_adb_command

ROOT = Path(__file__).resolve().parents[2]


@sentinel
def capture_screenshot(
    output_path: str | None = None, device_id: str | None = None
) -> dict[str, str]:
    destination = Path(output_path) if output_path else ROOT / "temp" / "android" / "screenshot.png"
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable adb side effects.",
            "output_path": str(destination),
        }

    command = adb_base_command(device_id) + ["exec-out", "screencap", "-p"]
    result = run_adb_command(command, text=False)
    if result is None:
        return {
            "status": "failed",
            "detail": "adb executable not found",
            "output_path": str(destination),
        }
    if result.returncode != 0:
        return {
            "status": "failed",
            "detail": result.stderr.decode(errors="ignore").strip() or "adb screencap failed",
            "output_path": str(destination),
        }

    destination.write_bytes(result.stdout)
    return {"status": "ok", "detail": "screenshot captured", "output_path": str(destination)}


__all__ = ["capture_screenshot"]
