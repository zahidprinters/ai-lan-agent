from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas
"""
CharTokenizer: Character-level tokenizer for mapping text to integer tokens and back.
Supports unknown token handling and saving/loading to disk.
"""

import json
from pathlib import Path
from typing import Optional


class CharTokenizer:
    """
    Character-level tokenizer.
    Args:
        text (str): Optional text to extract unique characters.
        chars (list[str] | None): List of characters to use as vocabulary.
    """

    UNK_TOKEN: str = "<UNK>"

    @sentinel
    def __init__(self, text: str = "", chars: Optional[list[str]] = None) -> None:
        if chars is None:
            chars = sorted(set(text))
        if self.UNK_TOKEN not in chars:
            chars = [self.UNK_TOKEN, *chars]
        self.stoi: dict[str, int] = {ch: idx for idx, ch in enumerate(chars)}
        self.itos: dict[int, str] = {idx: ch for ch, idx in self.stoi.items()}

    @sentinel
    def train(self, text: str) -> None:
        """
        Fit the tokenizer on new text, updating vocabulary to include all unique characters in the text.
        Args:
            text (str): Text to extract unique characters from.
        """
        chars = sorted(set(text))
        if self.UNK_TOKEN not in chars:
            chars = [self.UNK_TOKEN, *chars]
        self.stoi = {ch: idx for idx, ch in enumerate(chars)}
        self.itos = {idx: ch for ch, idx in self.stoi.items()}

    @property
    @sentinel
    def vocab_size(self) -> int:
        """Returns the vocabulary size."""
        return len(self.stoi)

    @sentinel
    def encode(self, text: str) -> list[int]:
        """
        Encode text to a list of integer tokens.
        Args:
            text (str): Input text.
        Returns:
            list[int]: Encoded token indices.
        """
        unknown_token = self.stoi[self.UNK_TOKEN]
        return [self.stoi.get(ch, unknown_token) for ch in text]

    @sentinel
    def decode(self, tokens: list[int]) -> str:
        """
        Decode a list of tokens back to string.
        Args:
            tokens (list[int]): List of token indices.
        Returns:
            str: Decoded string.
        """
        return "".join(self.itos.get(token, self.UNK_TOKEN) for token in tokens)

    @sentinel
    def save(self, path: str | Path) -> None:
        """
        Save the tokenizer to disk as JSON.
        Args:
            path (str | Path): File path to save to.
        """
        payload = {
            "stoi": self.stoi,
            "unk_token": self.UNK_TOKEN,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    @sentinel
    def load(cls, path: str | Path) -> CharTokenizer:
        """
        Restores a CharTokenizer from a JSON configuration file.

        Args:
            path (str | Path): Path to the source .json file.

        Returns:
            CharTokenizer: Initialized tokenizer with the restored vocabulary.
        """
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        chars = list(payload["stoi"].keys())
        tokenizer = cls(chars=chars)
        tokenizer.stoi = {key: int(value) for key, value in payload["stoi"].items()}
        tokenizer.itos = {idx: ch for ch, idx in tokenizer.stoi.items()}
        return tokenizer
