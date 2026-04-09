from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas
"""
CharMLP: A simple character-level MLP language model for sequence prediction.
Implements embedding, flattening, and two linear layers with ReLU activation.
"""

from typing import cast, Any
import torch
from torch import nn


class CharMLP(nn.Module):
    """
    Character-level MLP language model.
    Args:
        vocab_size (int): Number of unique tokens in the vocabulary.
        block_size (int): Length of input sequences.
        hidden_size (int): Size of the hidden layer.
    """

    @sentinel
    def __init__(self, vocab_size: int, block_size: int, hidden_size: int) -> None:
        super().__init__()
        self.block_size = block_size
        self.embedding: nn.Embedding = nn.Embedding(vocab_size, hidden_size)
        self.linear1: nn.Linear = nn.Linear(block_size * hidden_size, hidden_size)
        self.linear2: nn.Linear = nn.Linear(hidden_size, vocab_size)

    @sentinel
    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        past_key_values: Any = None,
        use_cache: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, None]:
        """
        Forward pass for CharMLP.
        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, seq_len).
            use_cache (bool): If True, returns (logits, None) for compatibility.
        Returns:
            torch.Tensor: Output logits of shape (batch_size, vocab_size).
        """
        batch_size, seq_len = x.shape

        # CharMLP requires exactly block_size context. Pad or slice.
        if seq_len < self.block_size:
            # Left pad with 0s (usually the padding/unknown token)
            padding = torch.zeros(
                (batch_size, self.block_size - seq_len), dtype=x.dtype, device=x.device
            )
            x = torch.cat([padding, x], dim=1)
        elif seq_len > self.block_size:
            x = x[:, -self.block_size :]

        h = self.embedding(x)
        h_flat = h.view(batch_size, -1)
        logits = torch.relu(self.linear1(h_flat))
        logits = cast(torch.Tensor, self.linear2(logits))

        # If it's a sequence, we only really predict the LAST token in this simple MLP
        # But for interface compatibility, we might need to return (batch, seq_len, vocab)
        # However, CharMLP only predicts ONE token based on the whole block.
        # Let's return (batch, 1, vocab) if it's supposed to be a sequence
        if logits.dim() == 2:
            logits = logits.unsqueeze(1)

        if use_cache:
            return logits, None
        return logits
