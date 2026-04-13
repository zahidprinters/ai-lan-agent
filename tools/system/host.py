from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import asdict, dataclass

from debug_utils import sentinel

DEFAULT_ALLOWED_APPS: dict[str, list[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "snippingtool": ["SnippingTool.exe"],
    "snipping-tool": ["SnippingTool.exe"],
    "vscode": ["Code.exe"],
    "code": ["Code.exe"],
}


@dataclass(frozen=True)
class AppLaunchSpec:
    canonical_name: str
    command: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _get_process_list_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS", "8").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 8
    return max(1, min(timeout, 60))


def _get_open_app_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_PC_OPEN_APP_TIMEOUT_SECONDS", "8").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 8
    return max(1, min(timeout, 60))


def _normalize_app_key(value: str) -> str:
    normalized = value.strip().lower()
    return "".join(char for char in normalized if char.isalnum())


def _load_allowed_app_specs() -> dict[str, AppLaunchSpec]:
    specs: dict[str, AppLaunchSpec] = {}
    for canonical_name, command in DEFAULT_ALLOWED_APPS.items():
        specs[_normalize_app_key(canonical_name)] = AppLaunchSpec(canonical_name, list(command))

    raw_aliases = os.getenv("AI_LAN_ALLOWED_APPS", "").strip()
    if not raw_aliases:
        return specs

    for item in raw_aliases.split(","):
        alias = item.strip()
        if not alias:
            continue
        if "=" in alias:
            canonical, command_text = alias.split("=", 1)
            canonical_name = canonical.strip()
            command = command_text.strip()
            if canonical_name and command:
                specs[_normalize_app_key(canonical_name)] = AppLaunchSpec(
                    canonical_name=canonical_name,
                    command=[command],
                )
            continue
        normalized = _normalize_app_key(alias)
        specs[normalized] = AppLaunchSpec(canonical_name=alias, command=[alias])
    return specs


@sentinel
def open_app(app_name: str) -> dict[str, object]:
    """Launch an allowlisted desktop application with bounded process creation."""
    requested_name = app_name.strip()
    if not requested_name:
        return {
            "status": "blocked_policy",
            "detail": "Application name cannot be empty.",
            "requested_app": app_name,
        }

    allowed_specs = _load_allowed_app_specs()
    spec = allowed_specs.get(_normalize_app_key(requested_name))
    if spec is None:
        allowed_names = sorted({entry.canonical_name for entry in allowed_specs.values()})
        return {
            "status": "blocked_policy",
            "detail": (
                "App is not on the allowlist. Set AI_LAN_ALLOWED_APPS to permit it."
            ),
            "requested_app": requested_name,
            "allowed_apps": allowed_names,
        }

    timeout_seconds = _get_open_app_timeout_seconds()
    try:
        process = subprocess.Popen(  # noqa: S603
            spec.command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return {
            "status": "failed",
            "detail": f"Launch target not found for '{requested_name}'.",
            "requested_app": requested_name,
            "launch_command": spec.command,
        }
    except OSError as exc:
        return {
            "status": "failed",
            "detail": f"Failed to launch '{requested_name}': {exc}",
            "requested_app": requested_name,
            "launch_command": spec.command,
        }

    return {
        "status": "ok",
        "detail": f"Launch requested for '{requested_name}'.",
        "requested_app": requested_name,
        "launch_command": spec.command,
        "pid": process.pid,
        "timeout_seconds": timeout_seconds,
    }


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
