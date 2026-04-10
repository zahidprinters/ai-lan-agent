from __future__ import annotations

import pytest

from debug_utils import _sanitize_trace_value


@pytest.mark.unit
def test_sanitize_masks_sensitive_variable_names() -> None:
    assert _sanitize_trace_value("api_key", "abc123") == "<masked>"
    assert _sanitize_trace_value("clipboard_text", "hello") == "<masked>"


@pytest.mark.unit
def test_sanitize_masks_sensitive_value_patterns() -> None:
    assert _sanitize_trace_value("payload", "Bearer SECRET_TOKEN") == "<masked>"
    assert _sanitize_trace_value("payload", "sk-abcdef123456") == "<masked>"


@pytest.mark.unit
def test_sanitize_truncates_long_non_sensitive_values() -> None:
    text = "x" * 150
    sanitized = _sanitize_trace_value("message", text)
    assert len(sanitized) <= 100
    assert sanitized.endswith("...")
