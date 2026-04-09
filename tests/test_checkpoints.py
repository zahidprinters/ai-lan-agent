# Copyright (c) 2026 Nadeem Abbas
"""
Unit tests for AI Lan checkpointing and experiment persistence.
Ensures that all metadata, config states, and model weights are preserved.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock
import torch
from training.checkpoints import (
    build_sorted_summaries,
    load_checkpoint,
    load_model_from_checkpoint,
    save_checkpoint,
    save_run_artifacts,
)
from training.config import ProjectConfig


class TestCheckpointing(unittest.TestCase):
    """
    Validates that the AI Lan persistence layer is robust and reproducible.
    """

    def setUp(self) -> None:
        self.temp_dir = Path("temp/test_runs")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.temp_dir / "test_checkpoint.pt"
        self.config = ProjectConfig(data_path=Path("data/input.txt"))

        # Proper model and tokenizer initialization
        from training.factory import build_model
        from tokenizer.char_tokenizer import CharTokenizer

        self.tokenizer = CharTokenizer("abc")

        self.model = build_model(
            "char_mlp", config=self.config, vocab_size=self.tokenizer.vocab_size
        )
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

    def test_checkpoint_roundtrip(self) -> None:
        """Ensures saving and loading a checkpoint preserves all data."""
        save_checkpoint(
            path=self.checkpoint_path,
            model=self.model,
            tokenizer=self.tokenizer,
            config=self.config,
            best_val_loss=0.5,
            model_type="transformer",
            optimizer=self.optimizer,
            epoch=5,
            best_val_perplexity=1.6,
        )

        self.assertTrue(self.checkpoint_path.exists())
        checkpoint = load_checkpoint(self.checkpoint_path)

        self.assertEqual(checkpoint["model_type"], "transformer")
        self.assertEqual(checkpoint["epoch"], 5)
        self.assertEqual(checkpoint["best_val_loss"], 0.5)
        self.assertIn("optimizer_state", checkpoint)
        self.assertEqual(checkpoint["tokenizer"]["vocab_size"], 4)

    def test_run_artifacts_creation(self) -> None:
        """Validates the creation of nested JSON summary artifacts."""
        timestamp = "20260401_000000"
        summary_path = self.config.runs_dir / f"{timestamp}_summary.json"

        save_run_artifacts(
            config=self.config,
            timestamp=timestamp,
            tokenizer=self.tokenizer,
            best_val_loss=0.4,
            final_train_loss=0.3,
            final_val_loss=0.4,
            sample_logs=["test sample"],
            train_tokens=100,
            val_tokens=10,
            model_type="transformer",
            project_data_path=Path("data/input.txt"),
        )

        self.assertTrue(summary_path.exists())
        with summary_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["metrics"]["best_val_loss"], 0.4)
            self.assertIn("system", data)
            self.assertIn("python_version", data["system"])

    def test_quantized_checkpoint_roundtrip(self) -> None:
        """Quantized checkpoints should reload through the shared loader."""
        save_checkpoint(
            path=self.checkpoint_path,
            model=self.model,
            tokenizer=self.tokenizer,
            config=self.config,
            best_val_loss=0.5,
            model_type="char_mlp",
            optimizer=self.optimizer,
            epoch=5,
            best_val_perplexity=1.6,
        )

        checkpoint = load_checkpoint(self.checkpoint_path)
        base_model, _, _ = load_model_from_checkpoint(
            checkpoint,
            tokenizer_vocab_size=self.tokenizer.vocab_size,
            allow_quantized=False,
        )
        quantized_model = torch.quantization.quantize_dynamic(
            base_model, {torch.nn.Linear}, dtype=torch.qint8
        )
        quantized_checkpoint = dict(checkpoint)
        quantized_checkpoint["model_state"] = quantized_model.state_dict()
        quantized_checkpoint["is_quantized"] = True

        loaded_model, loaded_config, loaded_vocab_size = load_model_from_checkpoint(
            quantized_checkpoint,
            tokenizer_vocab_size=self.tokenizer.vocab_size,
            allow_quantized=True,
        )

        self.assertEqual(loaded_config.block_size, self.config.block_size)
        self.assertEqual(loaded_vocab_size, self.tokenizer.vocab_size)
        self.assertIsNotNone(loaded_model)

    def test_build_sorted_summaries_normalizes_old_and_new_schemas(self) -> None:
        """Run summaries should normalize mixed legacy and nested schemas."""
        runs_dir = self.temp_dir / "schema_runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        legacy_summary = {
            "timestamp": "20260301_000000",
            "data_path": str(self.config.data_path),
            "best_val_loss": 1.2,
            "final_train_loss": 0.8,
            "final_val_loss": 1.1,
            "learning_rate": 0.001,
            "batch_size": 16,
            "block_size": 8,
            "hidden_size": 32,
        }
        nested_summary = {
            "timestamp": "20260401_000000",
            "metrics": {
                "best_val_loss": 0.4,
                "final_train_loss": 0.3,
                "final_val_loss": 0.4,
            },
            "hyperparameters": {
                "learning_rate": 0.002,
                "batch_size": 8,
                "block_size": 16,
                "hidden_size": 64,
            },
            "data": {
                "path": str(self.config.data_path),
                "size_bytes": 123,
                "train_token_count": 10,
                "val_token_count": 2,
                "vocab_size": 4,
            },
        }
        (runs_dir / "20260301_000000_summary.json").write_text(
            json.dumps(legacy_summary), encoding="utf-8"
        )
        (runs_dir / "20260401_000000_summary.json").write_text(
            json.dumps(nested_summary), encoding="utf-8"
        )

        summaries = build_sorted_summaries(runs_dir, self.config.data_path)

        self.assertEqual(len(summaries), 2)
        self.assertTrue(all("data_path" in entry for entry in summaries))
        self.assertTrue(all("final_train_loss" in entry for entry in summaries))
        self.assertTrue(
            any(entry["summary_file"] == "20260401_000000_summary.json" for entry in summaries)
        )


if __name__ == "__main__":
    unittest.main()
