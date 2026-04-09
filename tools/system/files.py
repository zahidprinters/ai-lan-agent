"""Workspace file and shell adapters."""

from __future__ import annotations

from pathlib import Path

from debug_utils import sentinel

ROOT = Path(__file__).resolve().parents[2]


@sentinel
def execute_shell(command: str) -> str:
    """Registers a shell command request without executing it."""
    print(f"[SystemFiles] Execute Shell: {command}")
    return f"STUB: Command '{command}' received but not executed for safety."


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
