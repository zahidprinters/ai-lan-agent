from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
"""
Tokenizer Factory for AI Lan.
Provides a unified interface for loading, saving, and initializing 
different tokenizer types (Char, BPE).
"""

from pathlib import Path
from typing import Union
from debug_utils import sentinel
from tokenizer.char_tokenizer import CharTokenizer
from tokenizer.bpe_tokenizer import BPETokenizer

TokenizerType = Union[CharTokenizer, BPETokenizer]


@sentinel
def load_tokenizer(path: Path | str) -> TokenizerType:
    """
    Dynamically loads the appropriate tokenizer based on file content
    and metadata.

    Args:
        path (Path | str): Path to the tokenizer file.

    Returns:
        TokenizerType: Loaded tokenizer instance.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tokenizer not found at: {path}")

    if path.suffix == ".json":
        import json

        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if "stoi" in content:
                return CharTokenizer.load(path)
            return BPETokenizer.load(path)
        except Exception:
            # Fallback to BPE if JSON parsing fails or other issues
            return BPETokenizer.load(path)

    return CharTokenizer.load(path)


@sentinel
def get_tokenizer_by_type(
    tokenizer_type: str, path: Path, corpus_text: str | None = None, corpus_path: Path | None = None
) -> TokenizerType:
    """
    Initializes or loads a tokenizer based on a specific type name.

    Args:
        tokenizer_type (str): 'char' or 'bpe'.
        path (Path): Path to save/load from.
        corpus_text (str): Required for initializing a fresh CharTokenizer.
        corpus_path (Path): Required for training a fresh BPETokenizer.

    Returns:
        TokenizerType: Initialized tokenizer.
    """
    if path.exists():
        return load_tokenizer(path)

    # Ensure parent directory exists for saving
    path.parent.mkdir(parents=True, exist_ok=True)

    if tokenizer_type == "bpe":
        if not corpus_path or not corpus_path.exists():
            raise ValueError("Corpus path required for training a new BPE tokenizer.")
        bpe = BPETokenizer(vocab_size=1000)
        bpe.train([str(corpus_path)])
        bpe.save(path)
        return bpe

    if not corpus_text:
        raise ValueError("Corpus text required for initializing a new Char tokenizer.")
    char_tok = CharTokenizer(corpus_text)
    char_tok.save(path)
    return char_tok
