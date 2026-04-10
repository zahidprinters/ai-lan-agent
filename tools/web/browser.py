"""Playwright browser automation facade for Phase 4 web tool use.

Provides a synchronous `browser_fetch` function that loads a URL with a
real Chromium browser (headless), returns the page text, and optionally
saves a screenshot.  Falls back to a plain ``requests`` GET if Playwright
is not available so the rest of the stack continues to work.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from debug_utils import sentinel

ROOT = Path(__file__).resolve().parents[3]
_PLAYWRIGHT_AVAILABLE: bool | None = None


def _playwright_available() -> bool:
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is None:
        try:
            import playwright  # noqa: F401

            _PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            _PLAYWRIGHT_AVAILABLE = False
    return bool(_PLAYWRIGHT_AVAILABLE)


def _allow_browser_navigation() -> bool:
    return os.getenv("AI_LAN_BROWSER_ALLOW", "1").strip() in {"1", "true", "True"}


@sentinel
def browser_fetch(
    url: str,
    *,
    screenshot_path: str | None = None,
    timeout_ms: int = 30_000,
) -> dict[str, Any]:
    """Fetch a URL with Playwright Chromium (headless).

    Returns a dict with keys:
      ``status``: "ok" | "failed" | "blocked"
      ``url``: the final URL (after redirects)
      ``text``: page text extracted from the DOM
      ``screenshot``: file path if a screenshot was saved, else None
      ``detail``: empty string on success, error message on failure
    """
    if not _allow_browser_navigation():
        return {
            "status": "blocked",
            "url": url,
            "text": "",
            "screenshot": None,
            "detail": "Set AI_LAN_BROWSER_ALLOW=1 to enable browser navigation.",
        }

    if not _playwright_available():
        # Graceful fallback to requests
        try:
            import requests  # type: ignore[import-untyped]

            response = requests.get(url, timeout=30, headers={"User-Agent": "AI-Lan/0.3"})
            response.raise_for_status()
            return {
                "status": "ok",
                "url": response.url,
                "text": response.text[:50_000],
                "screenshot": None,
                "detail": "playwright not installed; used requests fallback",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "url": url,
                "text": "",
                "screenshot": None,
                "detail": f"requests fallback failed: {exc}",
            }

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]

        shot_path: str | None = None

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            final_url: str = page.url
            page_text: str = page.inner_text("body")

            if screenshot_path:
                dest = Path(screenshot_path)
            else:
                dest = ROOT / "temp" / "browser" / "last_page.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(dest))
            shot_path = str(dest)

            browser.close()

        return {
            "status": "ok",
            "url": final_url,
            "text": page_text[:50_000],
            "screenshot": shot_path,
            "detail": "",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "url": url,
            "text": "",
            "screenshot": None,
            "detail": str(exc),
        }


__all__ = ["browser_fetch"]
