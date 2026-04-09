import os
import sys
import time
import math
import logging
import shutil
import torch
from torch import nn
from torch.utils.data import DataLoader
from datetime import datetime
from typing import cast
from typing import Any, Dict, List, Optional, Tuple

from debug_utils import sentinel
from training.config import ProjectConfig
from training.checkpoints import save_checkpoint
from training.inference import sample_text

LOGGER = logging.getLogger("sentinel")


class Trainer:
    """
    Modular training engine for AI Lan neural networks.

    Handles the training loop, validation cycles, early stopping, and
    learning rate scheduling with Mixed Precision (AMP) and optional
    Weights & Biases (wandb) experiment tracking.
    """

    @sentinel
    def __init__(
        self,
        config: ProjectConfig,
        model: nn.Module,
        tokenizer: Any,
        optimizer: torch.optim.Optimizer,
        loss_fn: nn.Module,
    ) -> None:
        self.config = config
        self.device: torch.device = torch.device(config.device)
        self.model: nn.Module = model.to(self.device)

        # Optimize model with torch.compile if supported (Python 3.10+, PyTorch 2.0+)
        should_try_compile = hasattr(torch, "compile") and sys.version_info >= (3, 10)
        # On Windows CPU builds, torch.compile may require the MSVC compiler (cl.exe).
        if should_try_compile and os.name == "nt" and shutil.which("cl") is None:
            should_try_compile = False
            LOGGER.info("Skipping torch.compile: cl.exe not found on Windows host.")

        if should_try_compile:
            try:
                LOGGER.info("Optimizing model with torch.compile...")
                self.model = cast(nn.Module, torch.compile(self.model))
            except Exception as e:
                LOGGER.warning(f"torch.compile failed: {e}. Falling back to standard model.")

        self.tokenizer: Any = tokenizer
        self.optimizer: torch.optim.Optimizer = optimizer
        self.loss_fn: nn.Module = loss_fn

        # Optional Experiment Tracking (WandB & MLflow)
        self.use_wandb: bool = os.getenv("AI_LAN_USE_WANDB", "0") == "1"
        self.use_mlflow: bool = os.getenv("AI_LAN_USE_MLFLOW", "0") == "1"

        if self.use_wandb:
            try:
                import wandb  # type: ignore[import-not-found]

                wandb.init(
                    project="ai-lan",
                    config=config.__dict__,
                    name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                )
            except ImportError:
                LOGGER.warning("wandb not installed. Disabling logger.")
                self.use_wandb = False

        if self.use_mlflow:
            try:
                import mlflow  # type: ignore[import-not-found]

                mlflow.set_tracking_uri("sqlite:///mlruns.db")
                mlflow.set_experiment("ai-lan")
                mlflow.start_run(run_name=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                mlflow.log_params(config.__dict__)
            except ImportError:
                LOGGER.warning("mlflow not installed. Disabling logger.")
                self.use_mlflow = False

        # Mixed Precision support (CUDA only)
        scaler_enabled = config.use_amp and self.device.type == "cuda"
        try:
            self.scaler: Any = torch.amp.GradScaler("cuda", enabled=scaler_enabled)
        except (AttributeError, TypeError):
            self.scaler = torch.cuda.amp.GradScaler(enabled=scaler_enabled)

        # Schedulers (Cosine Annealing with Warmup support)
        self.scheduler: torch.optim.lr_scheduler.CosineAnnealingLR = (
            torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=config.epochs, eta_min=config.learning_rate / 10
            )
        )

        # State tracking
        self.best_val_loss: float = float("inf")
        self.best_epoch: int = 0
        self.epochs_without_improvement: int = 0
        self.sample_logs: List[str] = []
        self.best_model_state: Optional[Dict[str, torch.Tensor]] = None

    @sentinel
    def evaluate(self, loader: DataLoader) -> float:
        """Calculates average loss over the validation dataset."""
        self.model.eval()
        total_loss: float = 0.0
        total_batches: int = 0

        device_type: str = self.device.type
        autocast_dtype: torch.dtype = torch.bfloat16 if device_type == "cpu" else torch.float16

        with torch.no_grad():
            with torch.autocast(
                device_type=device_type, dtype=autocast_dtype, enabled=self.config.use_amp
            ):
                for x_batch, y_batch in loader:
                    x_batch, y_batch = x_batch.to(self.device), y_batch.to(self.device)
                    logits: torch.Tensor = self.model(x_batch)
                    if logits.dim() == 3:
                        logits = logits[:, -1, :]
                    loss: torch.Tensor = self.loss_fn(logits, y_batch)
                    total_loss += loss.item()
                    total_batches += 1
        return total_loss / max(total_batches, 1)

    @sentinel
    def train_epoch(self, loader: DataLoader, current_step: int) -> Tuple[float, int]:
        """Executes a single training epoch with gradient scaling."""
        self.model.train()
        train_loss_total: float = 0.0
        train_batches: int = 0
        optimizer_steps: int = 0

        warmup_steps: int = getattr(self.config, "lr_warmup_steps", 0)
        warmup_epochs: int = getattr(self.config, "lr_warmup_epochs", 0)
        warmup_total: int = warmup_steps if warmup_steps > 0 else (warmup_epochs * len(loader))

        device_type: str = self.device.type
        autocast_dtype: torch.dtype = torch.bfloat16 if device_type == "cpu" else torch.float16

        for x_batch, y_batch in loader:
            x_batch, y_batch = x_batch.to(self.device), y_batch.to(self.device)

            if warmup_total > 0 and current_step < warmup_total:
                lr: float = self.config.learning_rate * min(1.0, (current_step + 1) / warmup_total)
                for param_group in self.optimizer.param_groups:
                    param_group["lr"] = lr

            current_step += 1

            with torch.autocast(
                device_type=device_type, dtype=autocast_dtype, enabled=self.config.use_amp
            ):
                logits: torch.Tensor = self.model(x_batch)
                if logits.dim() == 3:
                    logits = logits[:, -1, :]
                loss: torch.Tensor = self.loss_fn(logits, y_batch)

            if torch.isnan(loss):
                LOGGER.warning("Batch returned NaN loss at step %s; skipping batch.", current_step)
                continue

            self.optimizer.zero_grad()
            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            step_count_before: int = int(getattr(self.optimizer, "_step_count", 0))
            self.scaler.step(self.optimizer)
            self.scaler.update()
            step_count_after: int = int(getattr(self.optimizer, "_step_count", 0))
            if step_count_after > step_count_before:
                optimizer_steps += 1

            train_loss_total += loss.item()
            train_batches += 1

        # Only advance scheduler when a real optimizer step happened.
        if train_batches > 0 and optimizer_steps > 0:
            self.scheduler.step()
        return train_loss_total / max(train_batches, 1), current_step

    @sentinel
    def run(
        self, train_loader: DataLoader, val_loader: DataLoader, start_epoch: int = 1
    ) -> Tuple[float, float, float]:
        """Executes the full training loop with early stopping and tracking."""
        final_train_loss: float = 0.0
        final_val_loss: float = 0.0

        for epoch in range(start_epoch, self.config.epochs + 1):
            start_time: float = time.perf_counter()
            current_step: int = (epoch - 1) * len(train_loader)

            train_loss, _ = self.train_epoch(train_loader, current_step)
            val_loss: float = self.evaluate(val_loader)

            final_train_loss = train_loss
            final_val_loss = val_loss

            val_ppl: float = math.exp(val_loss) if val_loss < 20 else float("inf")
            epoch_time: float = time.perf_counter() - start_time
            current_lr: float = self.optimizer.param_groups[0]["lr"]

            print(
                f"Epoch {epoch}/{self.config.epochs} - {epoch_time:.1f}s - loss: {train_loss:.4f} - val_loss: {val_loss:.4f} - lr: {current_lr:.2e}"
            )

            # Optional WandB & MLflow Logging
            if self.use_wandb:
                import wandb

                wandb.log(
                    {
                        "epoch": epoch,
                        "train_loss": train_loss,
                        "val_loss": val_loss,
                        "val_perplexity": val_ppl,
                        "learning_rate": current_lr,
                        "epoch_duration": epoch_time,
                    }
                )

            if self.use_mlflow:
                import mlflow

                mlflow.log_metrics(
                    {
                        "train_loss": train_loss,
                        "val_loss": val_loss,
                        "val_ppl": val_ppl,
                        "lr": current_lr,
                    },
                    step=epoch,
                )

            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_epoch = epoch
                self.epochs_without_improvement = 0
                self.best_model_state = {
                    k: v.cpu().clone() for k, v in self.model.state_dict().items()
                }

                save_checkpoint(
                    path=self.config.best_model_path,
                    model=self.model,
                    optimizer=self.optimizer,
                    epoch=epoch,
                    best_val_loss=self.best_val_loss,
                    tokenizer=self.tokenizer,
                    config=self.config,
                    model_type=self.config.model_type,
                    best_val_perplexity=val_ppl,
                )
            else:
                self.epochs_without_improvement += 1

            if epoch % self.config.sample_every == 0:
                gen: str = sample_text(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    start_text=self.config.sample_start_text or "AI",
                    length=self.config.sample_length,
                    block_size=self.config.block_size,
                )
                self.sample_logs.append(f"Epoch {epoch}: {gen}")
                print(f"  [SAMPLE] {gen}")

            if self.epochs_without_improvement >= self.config.patience:
                print(
                    f"\n[INFO] Early stopping triggered. No improvement for {self.config.patience} epochs."
                )
                break

        if self.best_model_state:
            print(
                f"[INFO] Training concluded. Restoring best model state from epoch {self.best_epoch}."
            )
            self.model.load_state_dict(self.best_model_state)

        save_checkpoint(
            path=self.config.model_path,
            model=self.model,
            optimizer=self.optimizer,
            epoch=self.config.epochs,
            best_val_loss=self.best_val_loss,
            tokenizer=self.tokenizer,
            config=self.config,
            model_type=self.config.model_type,
        )

        if self.use_wandb:
            import wandb

            # In some versions wandb.finish() is needed
            wandb.finish()

        if self.use_mlflow:
            import mlflow

            mlflow.end_run()

        return self.best_val_loss, final_train_loss, final_val_loss
