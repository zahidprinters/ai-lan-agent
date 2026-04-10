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


def _get_adb_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_ANDROID_ADB_TIMEOUT_SECONDS", "15").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 15
    return max(1, min(timeout, 120))


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
    timeout_seconds = _get_adb_timeout_seconds()
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=text,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        detail = f"adb command timed out after {timeout_seconds}s"
        if text:
            return subprocess.CompletedProcess(command, 124, stdout="", stderr=detail)
        return subprocess.CompletedProcess(command, 124, stdout=b"", stderr=detail.encode("utf-8"))
    except FileNotFoundError:
        return None
