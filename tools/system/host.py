from __future__ import annotations

import os
import platform
import subprocess

from debug_utils import sentinel


def _get_process_list_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS", "8").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 8
    return max(1, min(timeout, 60))


@sentinel
def open_app(app_name: str) -> str:
    """Registers an application launch request without executing it."""
    print(f"[SystemHost] Open App: {app_name}")
    return f"STUB: App '{app_name}' launch request recorded but not executed for safety."


@sentinel
def get_system_status() -> dict[str, object]:
    """Returns local system metadata without changing machine state."""
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


@sentinel
def list_running_apps(limit: int = 25) -> list[str]:
    """Lists running process image names using tasklist in a read-only way."""
    command = ["tasklist", "/FO", "CSV", "/NH"]
    timeout_seconds = _get_process_list_timeout_seconds()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return [f"unavailable: tasklist timed out after {timeout_seconds}s"]
    except FileNotFoundError:
        return ["unavailable: tasklist not found"]

    if result.returncode != 0:
        return [f"unavailable: tasklist exit code {result.returncode}"]

    apps: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('"') and '","' in line:
            name = line.split('","', 1)[0].strip('"')
        else:
            name = line.split(",", 1)[0].strip('"')
        if name:
            apps.append(name)
        if len(apps) >= max(limit, 1):
            break
    return apps
