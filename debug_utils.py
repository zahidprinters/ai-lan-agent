"""Compatibility shim for legacy imports.

Canonical implementation now lives in ``core.utils.debug``.
"""

from core.utils.debug import (
    _sanitize_trace_value,
    ensure_project_temp,
    is_debug_enabled,
    is_profile_enabled,
    is_trace_enabled,
    psutil,
    sentinel,
)

__all__ = [
    "_sanitize_trace_value",
    "ensure_project_temp",
    "is_debug_enabled",
    "is_profile_enabled",
    "is_trace_enabled",
    "psutil",
    "sentinel",
]
