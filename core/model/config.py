"""Core config facade for model and inference settings."""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_type: str = "transformer"
    device: str = "cpu"
