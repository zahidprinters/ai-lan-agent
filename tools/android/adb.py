"""Android ADB adapters."""

from __future__ import annotations

from debug_utils import sentinel

from tools.android._common import adb_base_command, allow_side_effects, run_adb_command


@sentinel
def list_devices() -> list[dict[str, str]]:
    result = run_adb_command(["adb", "devices"], text=True)
    if result is None:
        return [
            {"device_id": "none", "status": "adb_unavailable", "detail": "adb executable not found"}
        ]
    if result.returncode != 0:
        return [
            {
                "device_id": "none",
                "status": "adb_unavailable",
                "detail": result.stderr.strip() or "adb command failed",
            }
        ]

    devices: list[dict[str, str]] = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"device_id": parts[0], "status": parts[1], "detail": ""})
    return devices


@sentinel
def launch_app(
    package_name: str, activity: str | None = None, device_id: str | None = None
) -> dict[str, str]:
    if not allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS=1 to enable adb side effects.",
        }

    component = f"{package_name}/{activity}" if activity else package_name
    command = adb_base_command(device_id) + ["shell", "am", "start", "-n", component]
    result = run_adb_command(command, text=True)
    if result is None:
        return {"status": "failed", "detail": "adb executable not found"}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "detail": (result.stdout or result.stderr).strip(),
    }


__all__ = ["list_devices", "launch_app"]
