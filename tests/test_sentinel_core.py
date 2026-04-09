from debug_utils import sentinel
import pytest


def test_sentinel_variable_trace(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_TRACE", "1")
    monkeypatch.setenv("AI_LAN_DEBUG", "1")
    monkeypatch.setenv("AI_LAN_TRACE_STDOUT", "1")

    @sentinel
    def sample_func(a: int) -> int:
        b = a + 1
        return b

    sample_func(5)
    captured = capsys.readouterr()
    # Check if variable 'b' assignment was captured
    assert "b = 6" in captured.out or "[TRACE] line" in captured.out
