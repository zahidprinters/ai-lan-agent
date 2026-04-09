"""Compatibility shim for legacy imports. Prefer tools/web/search.py."""

from tools.web.search import search_web

__all__ = ["search_web"]
