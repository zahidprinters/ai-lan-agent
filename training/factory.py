from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas

from torch import nn

from training.config import ProjectConfig

from training.models.bigram import BigramLanguageModel
from training.models.char_mlp import CharMLP
from training.models.transformer import StackedTransformer
from training.models.recurrent import LSTMModel, GRUModel

DEFAULT_MODEL_TYPE: str = "char_mlp"
BIGRAM_MODEL_TYPE: str = "bigram"
TRANSFORMER_MODEL_TYPE: str = "transformer"
LSTM_MODEL_TYPE: str = "lstm"
GRU_MODEL_TYPE: str = "gru"


@sentinel
def build_model(model_type: str, *, config: ProjectConfig, vocab_size: int) -> nn.Module:
    """
    Factory function to initialize neural architectures supported by AI Lan.

    Args:
        model_type (str): The identifier for the model (e.g., 'transformer', 'lstm').
        config (ProjectConfig): Experiment configuration containing dimensions.
        vocab_size (int): Size of the token vocabulary.

    Returns:
        nn.Module: Initialized PyTorch model instance.

    Raises:
        ValueError: If model_type is not recognized.
    """
    if model_type == DEFAULT_MODEL_TYPE:
        return CharMLP(
            vocab_size=vocab_size, block_size=config.block_size, hidden_size=config.hidden_size
        )
    if model_type == BIGRAM_MODEL_TYPE:
        return BigramLanguageModel(vocab_size=vocab_size)
    if model_type == TRANSFORMER_MODEL_TYPE:
        return StackedTransformer(
            vocab_size=vocab_size,
            block_size=config.block_size,
            hidden_size=config.hidden_size,
            num_layers=getattr(config, "n_layer", 2),
            num_heads=getattr(config, "n_head", 1),
            dropout=getattr(config, "dropout", 0.0),
            stochastic_depth=getattr(config, "stochastic_depth", 0.0),
        )
    if model_type == LSTM_MODEL_TYPE:
        return LSTMModel(
            vocab_size=vocab_size,
            hidden_size=config.hidden_size,
            num_layers=getattr(config, "n_layer", 2),
            dropout=getattr(config, "dropout", 0.0),
        )
    if model_type == GRU_MODEL_TYPE:
        return GRUModel(
            vocab_size=vocab_size,
            hidden_size=config.hidden_size,
            num_layers=getattr(config, "n_layer", 2),
            dropout=getattr(config, "dropout", 0.0),
        )
    raise ValueError(f"Unsupported model_type: {model_type}")
