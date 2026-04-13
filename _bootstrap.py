"""Compatibility shim for legacy imports.

Canonical implementation now lives in ``core.utils.bootstrap``.
"""

from core.utils.bootstrap import ensure_repo_root

__all__ = ["ensure_repo_root"]
