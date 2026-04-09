from __future__ import annotations

from debug_utils import sentinel

from pathlib import Path

import pytest

from training.corpus import analyze_text


@pytest.mark.unit
@sentinel
def test_corpus_report_counts_duplicates_and_suspicious_characters(tmp_path: Path) -> None:
    text = "alpha\n\nalpha\nbeta\t\nsnowman:\u2603\n"
    report = analyze_text(text, path=tmp_path / "input.txt")
    assert report.line_count == 5
    assert report.empty_line_count == 1
    assert report.duplicate_line_count == 1
    assert report.longest_line_length == len("snowman:\u2603")
    assert report.shortest_non_empty_line_length == len("alpha")
    assert any(ch == "\u2603" for ch, _ in report.suspicious_characters)
