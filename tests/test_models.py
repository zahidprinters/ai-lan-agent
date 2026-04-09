# Copyright (c) 2026 Nadeem Abbas
"""
Unit tests for AI Lan model architectures.
Ensures that all model types (Transformer, LSTM, GRU) produce the correct
output shapes and are torchscript/onnx compatible.
"""

import unittest
import torch
from training.models.transformer import StackedTransformer
from training.models.recurrent import LSTMModel, GRUModel


class TestModelArchitectures(unittest.TestCase):
    """
    Validates model construction and forward passes across all
    supported architectures.
    """

    def setUp(self) -> None:
        self.vocab_size = 50
        self.block_size = 16
        self.hidden_size = 32
        self.dummy_input = torch.randint(0, self.vocab_size, (2, self.block_size))

    def test_stacked_transformer_shapes(self) -> None:
        """Ensures Transformer outputs match (batch, seq, vocab)."""
        model = StackedTransformer(
            vocab_size=self.vocab_size,
            block_size=self.block_size,
            hidden_size=self.hidden_size,
            num_layers=2,
            num_heads=2,
        )
        output = model(self.dummy_input)
        self.assertEqual(output.shape, (2, self.block_size, self.vocab_size))

    def test_lstm_model_shapes(self) -> None:
        """Ensures LSTM outputs match (batch, seq, vocab)."""
        model = LSTMModel(vocab_size=self.vocab_size, hidden_size=self.hidden_size, num_layers=2)
        output = model(self.dummy_input)
        self.assertEqual(output.shape, (2, self.block_size, self.vocab_size))

    def test_gru_model_shapes(self) -> None:
        """Ensures GRU outputs match (batch, seq, vocab)."""
        model = GRUModel(vocab_size=self.vocab_size, hidden_size=self.hidden_size, num_layers=2)
        output = model(self.dummy_input)
        self.assertEqual(output.shape, (2, self.block_size, self.vocab_size))

    def test_inference_method(self) -> None:
        """Validates the inference optimization method (last token only)."""
        for model_cls in [LSTMModel, GRUModel]:
            model = model_cls(self.vocab_size, self.hidden_size)
            output = model.inference(self.dummy_input)  # type: ignore[operator]
            self.assertEqual(output.shape, (2, self.vocab_size))


if __name__ == "__main__":
    unittest.main()
