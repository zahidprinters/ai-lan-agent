from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas
"""
BPETokenizer: Byte-Pair Encoding tokenizer using HuggingFace tokenizers library.
Supports training, saving, loading, encoding, and decoding.
"""

from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders  # type: ignore[import-untyped]
from pathlib import Path
from typing import List, cast


class BPETokenizer:
    """
    Byte-Pair Encoding (BPE) tokenizer.
    Args:
        vocab_size (int): Number of merge operations/vocabulary size.
    """

    @sentinel
    def __init__(self, vocab_size: int = 1000) -> None:
        self.tokenizer: Tokenizer = Tokenizer(models.BPE())
        self.tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
        self.tokenizer.decoder = decoders.ByteLevel()
        self.vocab_size: int = vocab_size
        self.special_tokens: List[str] = [
            "<|endoftext|>",
            "[PAUSE]",
            "[THOUGHT]",
            "[ACTION]",
            "[OBSERVATION]",
        ]

    @sentinel
    def train(self, files: List[str]) -> None:
        """
        Train the BPE tokenizer on a list of files.
        Args:
            files (List[str]): List of file paths.
        """
        trainer = trainers.BpeTrainer(
            vocab_size=self.vocab_size, show_progress=True, special_tokens=self.special_tokens
        )
        self.tokenizer.train(files, trainer)

    @sentinel
    def save(self, path: Path) -> None:
        """
        Save the tokenizer to a single JSON file.
        Args:
            path (Path): File path to save to.
        """
        self.tokenizer.save(str(path))

    @classmethod
    @sentinel
    def load(cls, path: Path) -> BPETokenizer:
        """
        Restores a BPETokenizer from a JSON configuration file.

        Args:
            path (Path): Source .json file path.

        Returns:
            BPETokenizer: Initialized tokenizer with the restored BPE model.
        """
        tokenizer = Tokenizer.from_file(str(path))
        obj = cls()
        obj.tokenizer = tokenizer
        try:
            obj.vocab_size = int(tokenizer.get_vocab_size(with_added_tokens=True))
        except TypeError:
            obj.vocab_size = int(tokenizer.get_vocab_size())
        except Exception:
            obj.vocab_size = len(tokenizer.get_vocab())
        return obj

    @sentinel
    def encode(self, text: str) -> List[int]:
        """
        Encode text to a list of token ids.
        Args:
            text (str): Input text.
        Returns:
            List[int]: Encoded token ids.
        """
        return cast(List[int], self.tokenizer.encode(text).ids)

    @sentinel
    def decode(self, ids: List[int]) -> str:
        """
        Decode a list of token ids back to string.
        Args:
            ids (List[int]): List of token ids.
        Returns:
            str: Decoded string.
        """
        return cast(str, self.tokenizer.decode(ids))
