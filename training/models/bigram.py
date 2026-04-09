from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas
"""
BigramLanguageModel: A simple bigram language model using token embeddings.
Predicts the next token based only on the previous token.
"""

from typing import cast
import torch
from torch import nn


class BigramLanguageModel(nn.Module):
    """
    Bigram language model.
    Args:
        vocab_size (int): Number of unique tokens in the vocabulary.
    """

    @sentinel
    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.token_logits: nn.Embedding = nn.Embedding(vocab_size, vocab_size)

    @sentinel
    def forward(
        self, x: torch.Tensor, start_pos: int = 0, past_key_values=None, use_cache: bool = False
    ):
        """
        Forward pass for BigramLanguageModel.
        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, seq_len).
            start_pos (int): Ignored, for interface compatibility.
            past_key_values: Ignored, for interface compatibility.
            use_cache (bool): If True, return a tuple (logits, None) for compatibility.
        Returns:
            torch.Tensor or Tuple[torch.Tensor, None]: Output logits, and None if use_cache is True.
        """
        logits = cast(torch.Tensor, self.token_logits(x))
        if use_cache:
            return logits, None
        return logits

    @sentinel
    def inference(self, x: torch.Tensor) -> torch.Tensor:
        """
        Perform inference and return only the last logit.
        """
        logits = self.forward(x)
        return logits[:, -1, :]
