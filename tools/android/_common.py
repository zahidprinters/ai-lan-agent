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
