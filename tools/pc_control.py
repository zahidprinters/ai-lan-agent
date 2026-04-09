"""Compatibility shim for legacy imports. Prefer tools/system and tools/desktop modules."""

from tools.desktop.keyboard import type_text
from tools.desktop.mouse import move_mouse
from tools.system.clipboard import read_clipboard
from tools.system.files import execute_shell, list_workspace_files
from tools.system.host import get_system_status, list_running_apps, open_app

__all__ = [
    "execute_shell",
    "open_app",
    "type_text",
    "read_clipboard",
    "get_system_status",
    "list_running_apps",
    "list_workspace_files",
    "move_mouse",
]
