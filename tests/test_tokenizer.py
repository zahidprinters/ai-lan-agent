from __future__ import annotations

from debug_utils import sentinel
import pytest
from pathlib import Path
from tokenizer.char_tokenizer import CharTokenizer


@pytest.mark.unit
@sentinel
def test_tokenizer_round_trip_known_text() -> None:
    text = "AI engineering"
    tokenizer = CharTokenizer(text)
    encoded = tokenizer.encode(text)
    decoded = tokenizer.decode(encoded)
    assert decoded == text


@pytest.mark.unit
@sentinel
def test_tokenizer_uses_unknown_token_for_unseen_characters() -> None:
    tokenizer = CharTokenizer("abc")
    encoded = tokenizer.encode("abz")
    decoded = tokenizer.decode(encoded)
    assert decoded == "ab<UNK>"


@pytest.mark.unit
@sentinel
def test_saved_tokenizer_contains_input_characters(tmp_path: Path) -> None:
    text = "AI workflow"
    tokenizer = CharTokenizer(text)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    content = path.read_text(encoding="utf-8")
    for ch in set(text):
        assert ch in content
