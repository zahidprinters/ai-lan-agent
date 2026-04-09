from __future__ import annotations

import platform
import subprocess

from debug_utils import sentinel


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
    result = subprocess.run(command, capture_output=True, text=True, check=False)
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
