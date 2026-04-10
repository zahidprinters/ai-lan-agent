from __future__ import annotations

import os
import subprocess
from typing import Literal, overload


def adb_base_command(device_id: str | None = None) -> list[str]:
    base = ["adb"]
    if device_id:
        base.extend(["-s", device_id])
    return base


def allow_side_effects() -> bool:
    return os.getenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "0").strip() in {"1", "true", "True"}


def _parse_csv_allowlist(env_name: str) -> set[str]:
    raw_value = os.getenv(env_name, "")
    return {item.strip() for item in raw_value.split(",") if item.strip()}


def validate_allowed_device(device_id: str | None) -> dict[str, str] | None:
    allowed_devices = _parse_csv_allowlist("AI_LAN_ANDROID_ALLOWED_DEVICE_IDS")
    if not allowed_devices:
        return None
    if not device_id:
        return {
            "status": "blocked_policy",
            "detail": "Set device_id explicitly when AI_LAN_ANDROID_ALLOWED_DEVICE_IDS is configured.",
        }
    if device_id not in allowed_devices:
        return {
            "status": "blocked_policy",
            "detail": f"Android device '{device_id}' is not in AI_LAN_ANDROID_ALLOWED_DEVICE_IDS.",
        }
    return None


def validate_allowed_package(package_name: str) -> dict[str, str] | None:
    allowed_packages = _parse_csv_allowlist("AI_LAN_ANDROID_ALLOWED_PACKAGES")
    if not allowed_packages:
        return {
            "status": "blocked_policy",
            "detail": "Set AI_LAN_ANDROID_ALLOWED_PACKAGES to allow specific adb app launches.",
        }
    if package_name not in allowed_packages:
        return {
            "status": "blocked_policy",
            "detail": f"Android package '{package_name}' is not in AI_LAN_ANDROID_ALLOWED_PACKAGES.",
        }
    return None


@overload
def run_adb_command(
    command: list[str], *, text: Literal[True] = True
) -> subprocess.CompletedProcess[str] | None: ...


@overload
def run_adb_command(
    command: list[str], *, text: Literal[False]
) -> subprocess.CompletedProcess[bytes] | None: ...


def run_adb_command(
    command: list[str], *, text: bool = True
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(command, capture_output=True, text=text, check=False)
    except FileNotFoundError:
        return None
