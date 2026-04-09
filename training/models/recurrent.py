from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
"""
Recurrent Neural Network (RNN) Architectures for AI Lan.
Includes high-performance LSTM (Long Short-Term Memory) models for 
comparative sequence modeling.
"""

import torch
from torch import nn
from debug_utils import sentinel


class LSTMModel(nn.Module):
    """
    Multi-layer LSTM architecture with learned embeddings and Dropout.

    Args:
        vocab_size (int): Size of the token vocabulary.
        hidden_size (int): Dimension of the embedding and LSTM hidden state.
        num_layers (int): Number of stacked LSTM layers.
        dropout (float): Dropout probability between layers.
    """

    @sentinel
    def __init__(
        self, vocab_size: int, hidden_size: int, num_layers: int = 2, dropout: float = 0.2
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Linear(hidden_size, vocab_size)

    @sentinel
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Executes a recurrent forward pass with residual skip summation.

        This architecture uses learned embeddings followed by a multi-layer
        LSTM stack. To prevent gradient vanishing in deep recurrent paths,
        the embedding output is summed with the LSTM output before final
        linear projection.
        """
        x_emb = self.embedding(x)  # (batch, seq_len, hidden_size)

        # lstm_out: (batch, seq_len, hidden_size)
        lstm_out, _ = self.lstm(x_emb)

        # Residual Connection
        h = x_emb + lstm_out

        # logits: (batch, seq_len, vocab_size)
        logits = self.fc(h)
        return logits

    @sentinel
    def inference(self, x: torch.Tensor) -> torch.Tensor:
        """Inference pass returning only the final sequence logit."""
        logits = self.forward(x)
        return logits[:, -1, :]


class GRUModel(nn.Module):
    """
    Multi-layer Gated Recurrent Unit (GRU) with residual logic.

    Args:
        vocab_size (int): Size of the token vocabulary.
        hidden_size (int): Dimension of the embeddings and GRU hidden state.
        num_layers (int): Number of stacked GRU layers.
        dropout (float): Dropout probability between layers.
    """

    @sentinel
    def __init__(
        self, vocab_size: int, hidden_size: int, num_layers: int = 2, dropout: float = 0.2
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Linear(hidden_size, vocab_size)

    @sentinel
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Executes a gated recurrent forward pass with residual skip summation."""
        x_emb = self.embedding(x)
        gru_out, _ = self.gru(x_emb)

        # Residual Connection
        h = x_emb + gru_out

        logits = self.fc(h)
        return logits

    @sentinel
    def inference(self, x: torch.Tensor) -> torch.Tensor:
        """
        Inference pass that returns logits only for the last time step.
        """
        logits = self.forward(x)
        return logits[:, -1, :]
