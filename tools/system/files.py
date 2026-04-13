"""Workspace file and shell adapters."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from debug_utils import sentinel

ROOT = Path(__file__).resolve().parents[2]


def _get_shell_timeout_seconds() -> int:
    raw_value = os.getenv("AI_LAN_SHELL_TIMEOUT_SECONDS", "10").strip()
    try:
        timeout = int(raw_value)
    except ValueError:
        return 10
    return max(1, min(timeout, 120))


def _get_shell_output_limit() -> int:
    raw_value = os.getenv("AI_LAN_SHELL_OUTPUT_MAX_CHARS", "4000").strip()
    try:
        limit = int(raw_value)
    except ValueError:
        return 4000
    return max(256, min(limit, 20000))


def _truncate_output(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _get_shell_allowlist() -> set[str]:
    raw_value = os.getenv("AI_LAN_SHELL_ALLOWED_COMMANDS", "").strip()
    if not raw_value:
        return set()
    return {item.strip().lower() for item in raw_value.split(",") if item.strip()}


def _shell_is_enabled() -> bool:
    return os.getenv("AI_LAN_SHELL_ALLOW", "0").strip().lower() in {"1", "true", "yes", "on"}


def _extract_command_head(command: str) -> str:
    stripped = command.strip()
    if not stripped:
        return ""
    token = stripped.split(None, 1)[0]
    return token.strip().strip('"').strip("'").lower()


@sentinel
def execute_shell(command: str) -> dict[str, object]:
    """Execute an allowlisted shell command with bounded timeout and captured output."""
    normalized_command = command.strip()
    if not normalized_command:
        return {
            "status": "blocked_policy",
            "detail": "Shell command cannot be empty.",
            "command": command,
        }

    if not _shell_is_enabled():
        return {
            "status": "blocked_policy",
            "detail": "Shell execution is disabled. Set AI_LAN_SHELL_ALLOW=1 to enable it.",
            "command": normalized_command,
        }

    allowed_heads = _get_shell_allowlist()
    command_head = _extract_command_head(normalized_command)
    if not allowed_heads or command_head not in allowed_heads:
        return {
            "status": "blocked_policy",
            "detail": "Command head is not on the shell allowlist.",
            "command": normalized_command,
            "command_head": command_head,
            "allowed_commands": sorted(allowed_heads),
        }

    timeout_seconds = _get_shell_timeout_seconds()
    output_limit = _get_shell_output_limit()
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", normalized_command],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timed_out",
            "detail": f"Shell command timed out after {timeout_seconds}s.",
            "command": normalized_command,
            "command_head": command_head,
            "timeout_seconds": timeout_seconds,
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "detail": "powershell not found",
            "command": normalized_command,
            "command_head": command_head,
        }

    stdout = _truncate_output(
        result.stdout.replace("\r\n", "\n").replace("\r", "\n"),
        output_limit,
    )
    stderr = _truncate_output(
        result.stderr.replace("\r\n", "\n").replace("\r", "\n"),
        output_limit,
    )
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "detail": "Shell command completed." if result.returncode == 0 else "Shell command failed.",
        "command": normalized_command,
        "command_head": command_head,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timeout_seconds": timeout_seconds,
    }


@sentinel
def list_workspace_files(
    relative_path: str = ".",
    limit: int = 50,
    include_hidden: bool = False,
) -> dict[str, object]:
    """Lists files under the workspace root with path traversal blocked."""
    requested_path = (ROOT / relative_path).resolve()
    if requested_path != ROOT and ROOT not in requested_path.parents:
        return {
            "status": "blocked",
            "reason": "Path must stay inside the workspace root.",
            "path": relative_path,
            "entries": [],
        }

    if not requested_path.exists():
        return {
            "status": "not_found",
            "reason": "Requested path does not exist.",
            "path": relative_path,
            "entries": [],
        }

    if not requested_path.is_dir():
        return {
            "status": "not_directory",
            "reason": "Requested path is not a directory.",
            "path": relative_path,
            "entries": [],
        }

    entries: list[str] = []
    for child in sorted(
        requested_path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())
    ):
        if not include_hidden and child.name.startswith("."):
            continue
        entries.append(f"{child.name}/" if child.is_dir() else child.name)
        if len(entries) >= max(limit, 1):
            break

    relative_display = "."
    if requested_path != ROOT:
        relative_display = requested_path.relative_to(ROOT).as_posix()
    return {
        "status": "ok",
        "path": relative_display,
        "entries": entries,
    }


__all__ = ["execute_shell", "list_workspace_files"]
