"""Android screenshot adapter."""

from __future__ import annotations

from pathlib import Path

from debug_utils import sentinel

from tools.android._common import (
    adb_base_command,
    allow_side_effects,
    run_adb_command,
    validate_allowed_device,
)

ROOT = Path(__file__).resolve().parents[2]
TEMP_ROOT = (ROOT / "temp").resolve()


def _resolve_destination(output_path: str | None) -> Path:
    candidate = Path(output_path) if output_path else ROOT / "temp" / "android" / "screenshot.png"
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def _validate_destination(destination: Path) -> dict[str, str] | None:
    try:
        destination.relative_to(TEMP_ROOT)
    except ValueError:
        return {
            "status": "blocked_policy",
            "detail": "Android screenshots must be written under temp/.",
            "output_path": str(destination),
        }
    return None


@sentinel
def capture_screenshot(
    output_path: str | None = None, device_id: str | None = None
) -> dict[str, str]:
    destination = _resolve_destination(output_path)

    destination_violation = _validate_destination(destination)
    if destination_violation is not None:
        return destination_violation

    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable adb side effects.",
            "output_path": str(destination),
        }

    device_violation = validate_allowed_device(device_id)
    if device_violation is not None:
        device_violation["output_path"] = str(destination)
        return device_violation

    destination.parent.mkdir(parents=True, exist_ok=True)

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
