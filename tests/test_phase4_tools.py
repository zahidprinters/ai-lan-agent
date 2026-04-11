"""Unit tests for Phase 4 optional tool facades.

Covers: Tavily/DDG search backend selection, browser_fetch fallback,
OCR tool, scrcpy launcher guard, and policy/router registration.
"""

from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# web.search — backend selection
# ---------------------------------------------------------------------------

class TestWebSearchBackend:
    def test_ddg_fallback_used_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        from tools.web.search import _tavily_search

        result = _tavily_search("AI Lan", 3)
        assert result is None, "should return None (triggers DDG fallback) when no key"

    def test_tavily_returns_none_on_bad_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "INVALID_KEY_FOR_TEST")
        from tools.web.search import _tavily_search

        # Should not raise — returns None gracefully on any exception
        result = _tavily_search("AI Lan", 3)
        assert result is None or isinstance(result, list)

    def test_search_web_returns_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        def fake_ddg(query: str, max_results: int) -> list[dict[str, str]]:
            return [{"Title": query, "Snippet": "ok", "URL": "x"}]

        monkeypatch.setattr("tools.web.search._ddg_search", fake_ddg)
        from tools.web.search import search_web

        results = search_web("test", max_results=1)
        assert isinstance(results, list)
        assert results[0]["Title"] == "test"

    def test_search_web_uses_tavily_when_key_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TAVILY_API_KEY", "FAKE_KEY")
        expected = [{"Title": "T", "Snippet": "s", "URL": "u"}]

        monkeypatch.setattr("tools.web.search._tavily_search", lambda q, m: expected)
        from tools.web.search import search_web

        results = search_web("test", max_results=1)
        assert results == expected


# ---------------------------------------------------------------------------
# web.browser_fetch — safety guard and fallback
# ---------------------------------------------------------------------------

class TestBrowserFetch:
    def test_blocked_when_disallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_LAN_BROWSER_ALLOW", "0")
        from tools.web.browser import browser_fetch

        result = browser_fetch("https://example.com")
        assert result["status"] == "blocked"

    def test_requests_fallback_when_playwright_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_LAN_BROWSER_ALLOW", "1")
        # Force _PLAYWRIGHT_AVAILABLE to False
        import tools.web.browser as bmod
        monkeypatch.setattr(bmod, "_PLAYWRIGHT_AVAILABLE", False)

        class FakeResp:
            url = "https://example.com"
            text = "<html>hello</html>"

            def raise_for_status(self) -> None:
                pass

        def fake_get(url: str, **kw: object) -> FakeResp:
            return FakeResp()

        import requests
        monkeypatch.setattr(requests, "get", fake_get)

        from tools.web.browser import browser_fetch

        result = browser_fetch("https://example.com")
        # Either ok (fallback) or failed; important: no exception raised
        assert result["status"] in {"ok", "failed"}


# ---------------------------------------------------------------------------
# tools.perception.ocr — implementation
# ---------------------------------------------------------------------------

class TestOcrTool:
    def test_run_ocr_missing_file(self) -> None:
        from tools.perception.ocr import run_ocr

        result = run_ocr("/nonexistent/path/image.png")
        assert result["status"] == "failed"
        assert result["text"] == ""

    def test_run_ocr_returns_dict_shape(self) -> None:
        from tools.perception.ocr import run_ocr

        result = run_ocr("/nonexistent.png")
        assert "status" in result
        assert "text" in result
        assert "detail" in result

    def test_run_ocr_from_screenshot_returns_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from tools.perception.ocr import run_ocr_from_screenshot

        # If mss or tesseract not configured, should still return a valid dict
        result = run_ocr_from_screenshot()
        assert isinstance(result, dict)
        assert "status" in result

    def test_run_ocr_with_confidence_returns_expected_shape(self) -> None:
        from tools.perception.ocr import run_ocr_with_confidence

        result = run_ocr_with_confidence("/nonexistent.png", min_confidence=50.0)
        assert "status" in result
        assert "text" in result
        assert "filtered_text" in result
        assert "average_confidence" in result
        assert "tokens_considered" in result
        assert "tokens_kept" in result
        assert "detail" in result

    def test_run_ocr_with_confidence_rejects_unknown_backend(self) -> None:
        from tools.perception.ocr import run_ocr_with_confidence

        result = run_ocr_with_confidence("/nonexistent.png", backend="invalid")
        assert result["status"] == "failed"
        assert "Unsupported OCR backend" in str(result["detail"])

    def test_run_ocr_with_confidence_auto_falls_back_on_empty_tesseract(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        image_path = tmp_path / "sample.png"
        image_path.write_bytes(b"fake-image")
        monkeypatch.setattr("tools.perception.ocr._configure_tesseract", lambda: None)
        monkeypatch.setattr(
            "tools.perception.ocr._extract_tesseract_confidence",
            lambda image_path, *, min_confidence: {
                "status": "ok",
                "text": "",
                "filtered_text": "",
                "average_confidence": None,
                "tokens_considered": 0,
                "tokens_kept": 0,
                "detail": "",
                "backend": "tesseract",
            },
        )
        monkeypatch.setattr(
            "tools.perception.ocr._extract_easyocr_confidence",
            lambda image_path, *, min_confidence: {
                "status": "ok",
                "text": "fallback text",
                "filtered_text": "fallback text",
                "average_confidence": 92.0,
                "tokens_considered": 2,
                "tokens_kept": 2,
                "detail": "",
                "backend": "easyocr",
            },
        )

        from tools.perception.ocr import run_ocr_with_confidence

        result = run_ocr_with_confidence(str(image_path), backend="auto")
        assert result["status"] == "ok"
        assert result["backend"] == "easyocr"
        assert result["filtered_text"] == "fallback text"


# ---------------------------------------------------------------------------
# tools.android.scrcpy — safety guard
# ---------------------------------------------------------------------------

class TestScrcpyFacade:
    def test_blocked_in_safe_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "0")
        from tools.android.scrcpy import start_mirror

        result = start_mirror()
        assert result["status"] == "blocked_safe_mode"

    def test_fails_gracefully_when_binary_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
        monkeypatch.setattr("shutil.which", lambda _: None)
        from tools.android.scrcpy import start_mirror

        result = start_mirror()
        assert result["status"] == "failed"
        assert "scrcpy" in result["detail"]


class TestAndroidAdapterGuards:
    def test_capture_screenshot_blocks_paths_outside_temp(self) -> None:
        from tools.android.screen import capture_screenshot

        result = capture_screenshot(output_path="models/android.png")
        assert result["status"] == "blocked_policy"
        assert "temp/" in result["detail"]

    def test_tap_screen_blocks_negative_coordinates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
        from tools.android.input import tap_screen

        result = tap_screen(-1, 25)
        assert result["status"] == "blocked_policy"

    def test_swipe_screen_blocks_unapproved_device(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
        monkeypatch.setenv("AI_LAN_ANDROID_ALLOWED_DEVICE_IDS", "device-1")
        from tools.android.input import swipe_screen

        result = swipe_screen(1, 2, 3, 4, device_id="device-2")
        assert result["status"] == "blocked_policy"


# ---------------------------------------------------------------------------
# router.dispatch_core — new tools registered and policy-gated
# ---------------------------------------------------------------------------

class TestPhase4ToolsInRouter:
    def test_browser_fetch_in_registry(self) -> None:
        from router.dispatch_core import TOOL_REGISTRY

        assert "web.browser_fetch" in TOOL_REGISTRY

    def test_ocr_tools_in_registry(self) -> None:
        from router.dispatch_core import TOOL_REGISTRY

        assert "pc.ocr_image" in TOOL_REGISTRY
        assert "pc.ocr_screen" in TOOL_REGISTRY

    def test_scrcpy_mirror_in_registry(self) -> None:
        from router.dispatch_core import TOOL_REGISTRY

        assert "android.scrcpy_mirror" in TOOL_REGISTRY

    def test_browser_fetch_requires_confirmation(self) -> None:
        from safety.policy_engine import CONFIRMATION_REQUIRED_ACTIONS

        assert "web.browser_fetch" in CONFIRMATION_REQUIRED_ACTIONS

    def test_scrcpy_mirror_requires_confirmation(self) -> None:
        from safety.policy_engine import CONFIRMATION_REQUIRED_ACTIONS

        assert "android.scrcpy_mirror" in CONFIRMATION_REQUIRED_ACTIONS

    def test_ocr_tools_are_allowed_without_confirmation(self) -> None:
        from safety.policy_engine import ALLOWED_ACTIONS, CONFIRMATION_REQUIRED_ACTIONS

        assert "pc.ocr_image" in ALLOWED_ACTIONS
        assert "pc.ocr_screen" in ALLOWED_ACTIONS
        assert "pc.ocr_image" not in CONFIRMATION_REQUIRED_ACTIONS
        assert "pc.ocr_screen" not in CONFIRMATION_REQUIRED_ACTIONS

    def test_browser_fetch_dispatch_requires_confirmation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
        from router.dispatch_core import dispatch_agent_action

        result = dispatch_agent_action(
            {
                "thought": "Fetch a web page.",
                "action": "web.browser_fetch",
                "args": {"url": "https://example.com"},
                "safety_level": "medium",
            }
        )
        assert result.status == "confirmation_required"

    def test_browser_fetch_executes_when_confirmed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
        monkeypatch.setenv("AI_LAN_BROWSER_ALLOW", "1")

        import tools.web.browser as bmod
        monkeypatch.setattr(bmod, "_PLAYWRIGHT_AVAILABLE", False)

        import requests
        class FakeResp:
            url = "https://example.com"
            text = "ok"
            def raise_for_status(self) -> None: ...
        monkeypatch.setattr("requests.get", lambda *a, **k: FakeResp())

        from router.dispatch_core import dispatch_agent_action

        result = dispatch_agent_action(
            {
                "thought": "Fetch confirmed.",
                "action": "web.browser_fetch",
                "args": {"url": "https://example.com"},
                "safety_level": "medium",
            },
            confirmed=True,
        )
        assert result.status == "executed"
        assert isinstance(result.observation, dict)
