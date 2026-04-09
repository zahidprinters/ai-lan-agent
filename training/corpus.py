from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas

import json
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CorpusReport:
    """Dataclass holding statistical analysis of a text corpus."""

    path: Path
    total_characters: int
    unique_characters: int
    line_count: int
    non_empty_line_count: int
    empty_line_count: int
    duplicate_line_count: int
    longest_line_length: int
    shortest_non_empty_line_length: int
    top_characters: list[tuple[str, int]]
    rare_characters: list[tuple[str, int]]
    suspicious_characters: list[tuple[str, int]]


@sentinel
def merge_raw_corpus(raw_dir: Path, output_path: Path) -> None:
    """
    Merge all .txt files in raw_dir into a single cleaned output_path.
    """
    files = sorted(raw_dir.glob("*.txt"))
    with output_path.open("w", encoding="utf-8") as out:
        for file in files:
            text = file.read_text(encoding="utf-8")
            out.write(text.strip() + "\n")


@sentinel
def _is_suspicious_character(ch: str) -> bool:
    """Identifies control characters or high-unicode points."""
    if ch in {"\n", "\r", "\t"}:
        return False
    category = unicodedata.category(ch)
    return category.startswith("C") or ord(ch) > 126


@sentinel
def _format_character(ch: str) -> str:
    """Returns a human-readable label for whitespace/control chars."""
    names = {"\n": "\\n", "\r": "\\r", "\t": "\\t", " ": "<space>"}
    return names.get(ch, ch)


@sentinel
def _format_pairs(pairs: Iterable[tuple[str, int]]) -> str:
    """Formats character-count pairs for display."""
    values = [f"{_format_character(ch)}:{count}" for ch, count in pairs]
    return ", ".join(values) if values else "none"


@sentinel
def analyze_text(text: str, *, path: Path) -> CorpusReport:
    """
    Performs deep statistical analysis on a block of text.

    Args:
        text (str): Raw corpus text.
        path (Path): Source path reference.

    Returns:
        CorpusReport: Aggregated statistics.
    """
    lines = text.splitlines()
    char_counter = Counter(text)
    non_empty_lines = [line for line in lines if line.strip()]
    line_counter = Counter(line for line in lines if line.strip())

    duplicate_line_count = sum(count - 1 for count in line_counter.values() if count > 1)
    longest_line_length = max((len(line) for line in lines), default=0)
    shortest_non_empty_line_length = min((len(line) for line in non_empty_lines), default=0)

    top_characters = sorted(char_counter.items(), key=lambda item: (-item[1], item[0]))[:10]
    rare_characters = sorted(
        [(ch, count) for ch, count in char_counter.items() if count <= 2],
        key=lambda item: (item[1], item[0]),
    )[:10]
    suspicious_characters = sorted(
        [(ch, count) for ch, count in char_counter.items() if _is_suspicious_character(ch)],
        key=lambda item: (-item[1], item[0]),
    )

    return CorpusReport(
        path=path,
        total_characters=len(text),
        unique_characters=len(char_counter),
        line_count=len(lines),
        non_empty_line_count=len(non_empty_lines),
        empty_line_count=len(lines) - len(non_empty_lines),
        duplicate_line_count=duplicate_line_count,
        longest_line_length=longest_line_length,
        shortest_non_empty_line_length=shortest_non_empty_line_length,
        top_characters=top_characters,
        rare_characters=rare_characters,
        suspicious_characters=suspicious_characters,
    )


@sentinel
def analyze_file(path: Path) -> CorpusReport:
    """Reads a file and returns its analysis report."""
    return analyze_text(path.read_text(encoding="utf-8"), path=path)


@sentinel
def format_report(report: CorpusReport) -> str:
    """Converts a CorpusReport into a formatted string for dashboard output."""
    lines = [
        "AI Lan data report",
        f"path: {report.path}",
        f"total_characters: {report.total_characters}",
        f"unique_characters: {report.unique_characters}",
        f"line_count: {report.line_count}",
        f"non_empty_line_count: {report.non_empty_line_count}",
        f"empty_line_count: {report.empty_line_count}",
        f"duplicate_line_count: {report.duplicate_line_count}",
        f"longest_line_length: {report.longest_line_length}",
        f"shortest_non_empty_line_length: {report.shortest_non_empty_line_length}",
        f"top_characters: {_format_pairs(report.top_characters)}",
        f"rare_characters: {_format_pairs(report.rare_characters)}",
        f"suspicious_characters: {_format_pairs(report.suspicious_characters)}",
    ]
    return "\n".join(lines)
