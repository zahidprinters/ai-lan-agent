# Copyright (c) 2026 Nadeem Abbas
"""
Integration tests for AI Lan deployment workflows.
Validates ONNX export, and Quantization pipelines.
"""

import os
import unittest
import importlib.util
from pathlib import Path
import torch
from scripts.export_onnx import export_onnx
from scripts.quantize_model import quantize_model
from training.config import load_config, ProjectConfig
from training.factory import build_model
from tokenizer.factory import load_tokenizer


class TestDeploymentWorkflows(unittest.TestCase):
    """
    Ensures that models can be correctly exported and quantized
    for production deployment.
    """

    config: ProjectConfig
    vocab_size: int
    model: torch.nn.Module
    dummy_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        # Create a tiny dummy model for testing
        cls.vocab_size = 100
        cls.model = build_model("char_mlp", config=cls.config, vocab_size=cls.vocab_size)
        cls.dummy_path = Path("temp/test_model.pt")
        cls.dummy_path.parent.mkdir(parents=True, exist_ok=True)

        # Save dummy checkpoint
        checkpoint = {
            "model_state": cls.model.state_dict(),
            "model_type": "char_mlp",
            "config": cls.config.__dict__,
            "tokenizer": {"stoi": {"a": 0}, "vocab_size": cls.vocab_size},
        }
        torch.save(checkpoint, cls.dummy_path)

    def test_onnx_export_pipeline(self) -> None:
        """Validates the full ONNX export flow."""
        if importlib.util.find_spec("onnx") is None:
            self.skipTest("onnx is not installed; ONNX export is optional in this environment.")
        export_path = Path("temp/test_model.onnx")
        if export_path.exists():
            export_path.unlink()

        # Should NOT raise an exception
        # Signature: export_onnx(model_path: Path, onnx_path: Path, config: ProjectConfig)
        export_onnx(self.dummy_path, export_path, self.config)
        self.assertTrue(export_path.exists(), "ONNX file was not created.")

    def test_quantization_pipeline(self) -> None:
        """Validates the dynamic 8-bit quantization flow."""
        quant_path = Path("temp/test_model_quantized.pt")
        if quant_path.exists():
            quant_path.unlink()

        # Should NOT raise an exception
        # Signature: quantize_model(model_path: Path, quantized_path: Path, config: ProjectConfig)
        quantize_model(self.dummy_path, quant_path, self.config)
        self.assertTrue(quant_path.exists(), "Quantized model was not created.")

        # Verify it can be loaded
        q_checkpoint = torch.load(quant_path, weights_only=False)
        self.assertIn("model_state", q_checkpoint)


if __name__ == "__main__":
    unittest.main()
