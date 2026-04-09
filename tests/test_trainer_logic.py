# Copyright (c) 2026 Nadeem Abbas
"""
Unit tests for Trainer logic: Early Stopping and LR Scheduling.
Uses mocking to validate state transitions without actual compute.
"""

import unittest
from unittest.mock import MagicMock, patch
import torch
from training.trainer import Trainer
from training.config import ProjectConfig


class TestTrainerLogic(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ProjectConfig(
            epochs=10, learning_rate=1e-3, patience=2, device="cpu", use_amp=False, sample_every=5
        )

        self.model = MagicMock(spec=torch.nn.Module)
        self.model.parameters.return_value = []
        self.model.state_dict.return_value = {}

        self.optimizer = MagicMock(spec=torch.optim.Optimizer)
        self.optimizer.param_groups = [{"lr": 1e-3}]

        self.loss_fn = MagicMock(spec=torch.nn.Module)
        self.tokenizer = MagicMock()

    def test_early_stopping_trigger(self) -> None:
        """Validates that early stopping triggers after 'patience' epochs."""
        trainer = Trainer(self.config, self.model, self.tokenizer, self.optimizer, self.loss_fn)

        # Mocking train_epoch and evaluate
        trainer.train_epoch = MagicMock(return_value=(0.5, 10))  # type: ignore[method-assign]
        # Validation loss stays high
        trainer.evaluate = MagicMock(return_value=1.0)  # type: ignore[method-assign]

        # Run for 5 epochs, but patience is 2
        # We need to mock the save_checkpoint to avoid IO
        with patch("training.trainer.save_checkpoint"):
            trainer.run(MagicMock(), MagicMock(), start_epoch=1)

        # Should have stopped early (around epoch 3-4)
        self.assertLess(trainer.best_epoch + trainer.epochs_without_improvement, 10)
        self.assertEqual(trainer.epochs_without_improvement, self.config.patience)

    def test_learning_rate_warmup(self) -> None:
        """Validates that LR warmup correctly scales the learning rate."""
        # Create a new config for this test since it's frozen
        from dataclasses import replace

        test_config = replace(self.config, lr_warmup_steps=10)

        trainer = Trainer(test_config, self.model, self.tokenizer, self.optimizer, self.loss_fn)

        loader_mock = [(torch.zeros(1, 1), torch.zeros(1, dtype=torch.long))]

        # Mocking model forward and loss
        self.model.return_value = torch.zeros(1, 1, 10, requires_grad=True)
        self.loss_fn.return_value = torch.tensor(0.5, requires_grad=True)

        # Step 0: LR should be small
        _, next_step = trainer.train_epoch(loader_mock, current_step=0)  # type: ignore[arg-type]
        # 1/10 of base LR for the first step (step 1 / warmup_total 10)
        expected_lr = self.config.learning_rate * (1 / 10)
        self.assertAlmostEqual(self.optimizer.param_groups[0]["lr"], expected_lr, places=5)


if __name__ == "__main__":
    unittest.main()
