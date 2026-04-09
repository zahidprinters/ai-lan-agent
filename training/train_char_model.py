from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
import math
import os
from pathlib import Path
from datetime import datetime
from typing import Any
import torch
from torch import nn
from torch.utils.data import DataLoader

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()

from debug_utils import sentinel, ensure_project_temp

# from project_temp import ensure_project_temp # DELETED
from tokenizer.factory import get_tokenizer_by_type
from training.checkpoints import (
    load_checkpoint,
    load_config_from_checkpoint,
    load_model_from_checkpoint,
    save_run_artifacts,
)
from training.config import load_config
from training.dataset import CharSequenceDataset, split_tokens
from training.factory import build_model
from training.metrics import classify_overfit_gap
from training.trainer import Trainer

CONFIG = load_config()
TEMP_DIR = ensure_project_temp(ROOT)


@sentinel
def print_corpus_stats(text: str, tokens: list[int], tokenizer: Any) -> None:
    """Prints key statistics about the training corpus."""
    lines = text.splitlines()
    char_count = len(text)
    vocab_size = getattr(tokenizer, "vocab_size", len(set(tokens)))
    line_count = len(lines)
    empty_lines = sum(1 for l in lines if not l.strip())
    dupe_lines = line_count - len(set(l for l in lines if l.strip()))
    max_line = max((len(l) for l in lines if l.strip()), default=0)

    print("-" * 64)
    print("[CORPUS STATS]")
    print(f"  Characters: {char_count}")
    print(f"  Vocab size: {vocab_size}")
    print(f"  Lines: {line_count} (Empty: {empty_lines}, Duplicate: {dupe_lines})")
    print(f"  Longest entry: {max_line} characters")
    print("-" * 64)


@sentinel
def show_training_header() -> None:
    """Displays project and configuration info before training starts."""
    print("=" * 64)
    print(f"*** AI LAN - TRAINING MODULE - v{CONFIG.version}")
    print("=" * 64)
    print(f"[INFO] Data:   {CONFIG.data_path}")
    print(f"[INFO] Runs:   {CONFIG.runs_dir}")
    print(f"[INFO] Device: {CONFIG.device.upper()}")
    print("-" * 64)
    print(f"[INFO] Profile: {os.getenv('AI_LAN_EXP_PROFILE', 'default')}")
    print(f"[INFO] Model:   {CONFIG.model_type} (Layers: {CONFIG.n_layer}, Heads: {CONFIG.n_head})")
    print(
        f"[INFO] LR:      {CONFIG.learning_rate} (Epochs: {CONFIG.epochs}, Batch: {CONFIG.batch_size})"
    )
    print("=" * 64)


@sentinel
def show_run_summary(
    best_loss: float, train_loss: float, val_loss: float, gap: float, warning: str
) -> None:
    """Displays a professional table with final training metrics."""
    best_ppl = math.exp(best_loss) if best_loss < 20 else float("inf")

    print("\n" + "=" * 64)
    print("--- TRAINING RUN SUMMARY ---")
    print("=" * 64)
    print(f"| Metric           | Value            | Status          |")
    print(f"|------------------|------------------|-----------------|")
    print(
        f"| Best Loss        | {best_loss:16.4f} | {'* BEST' if best_loss == val_loss else 'VALID'} |"
    )
    print(f"| Best Perplexity  | {best_ppl:16.4f} | {'* IDEAL' if best_ppl < 5 else 'READY'} |")
    print(f"| Train Loss       | {train_loss:16.4f} | {'FINAL'} |")
    print(f"| Val Loss         | {val_loss:16.4f} | {'FINAL'} |")
    print(f"| Generaliz. Gap   | {gap:16.4f} | {warning.upper():15} |")
    print("=" * 64)
    print(f"[SUCCESS] Artifacts archived to: {CONFIG.runs_dir}")
    print("=" * 64 + "\n")


@sentinel
def main() -> None:
    """Main training entry point."""
    global CONFIG

    resume_checkpoint = None
    resume_config = CONFIG
    if CONFIG.best_model_path.exists():
        try:
            print(f"[INFO] Resuming metadata from checkpoint: {CONFIG.best_model_path}")
            resume_checkpoint = load_checkpoint(CONFIG.best_model_path)
            resume_config = load_config_from_checkpoint(resume_checkpoint, fallback=CONFIG)
        except Exception as e:
            print(f"[WARN] Failed to inspect checkpoint metadata: {e}. Starting fresh.")
            resume_checkpoint = None
            resume_config = CONFIG

    CONFIG = resume_config
    show_training_header()

    # Load data
    if not CONFIG.data_path.exists():
        raise FileNotFoundError(f"Training data not found: {CONFIG.data_path}")
    text = CONFIG.data_path.read_text(encoding="utf-8")

    # Tokenizer setup
    tokenizer_type = os.getenv("AI_LAN_TOKENIZER_TYPE", "char").lower()
    tokenizer_path = (
        resume_config.tokenizer_path
        if resume_config.tokenizer_path.exists()
        else CONFIG.tokenizer_path
    )
    tokenizer = get_tokenizer_by_type(
        tokenizer_type=tokenizer_type,
        path=tokenizer_path,
        corpus_text=text,
        corpus_path=CONFIG.data_path,
    )

    tokens = tokenizer.encode(text)
    token_split = split_tokens(tokens, resume_config.block_size, resume_config.train_ratio)
    print_corpus_stats(text, tokens, tokenizer)

    # DataLoaders
    train_dataset = CharSequenceDataset(token_split.train_tokens, resume_config.block_size)
    val_dataset = CharSequenceDataset(token_split.val_tokens, resume_config.block_size)
    train_loader = DataLoader(
        train_dataset, batch_size=resume_config.batch_size, shuffle=True, drop_last=True
    )
    val_loader = DataLoader(val_dataset, batch_size=resume_config.batch_size, shuffle=False)

    # Model and Optimizer
    vocab_size = getattr(tokenizer, "vocab_size", len(set(tokens)))
    if resume_checkpoint is not None:
        try:
            model, resume_config, _ = load_model_from_checkpoint(
                resume_checkpoint,
                tokenizer_vocab_size=vocab_size,
                fallback_config=resume_config,
                allow_quantized=False,
            )
        except ValueError as e:
            print(f"[WARN] {e} Starting fresh.")
            resume_checkpoint = None
            model = build_model(
                resume_config.model_type, config=resume_config, vocab_size=vocab_size
            )
        else:
            print(
                f"[INFO] Resumed model architecture from checkpoint config: {resume_config.model_type}"
            )
    else:
        model = build_model(resume_config.model_type, config=resume_config, vocab_size=vocab_size)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=resume_config.learning_rate, weight_decay=1e-2
    )
    start_epoch = 1

    # Resume from checkpoint
    if resume_checkpoint is not None:
        try:
            print(f"[INFO] Resuming optimizer state from checkpoint: {CONFIG.best_model_path}")
            if "optimizer_state" in resume_checkpoint:
                optimizer.load_state_dict(resume_checkpoint["optimizer_state"])
            start_epoch = resume_checkpoint.get("epoch", 0) + 1
            print(f"[INFO] Resumed at epoch {start_epoch}")
        except Exception as e:
            print(f"[WARN] Failed to load checkpoint: {e}. Starting fresh.")

    # Training
    trainer = Trainer(CONFIG, model, tokenizer, optimizer, nn.CrossEntropyLoss())
    best_loss, final_train_loss, final_val_loss = trainer.run(train_loader, val_loader, start_epoch)

    # Overfitting analysis
    train_val_gap = final_val_loss - final_train_loss
    overfit_band = classify_overfit_gap(train_val_gap)
    overfit_warning = {
        "ok": "optimal",
        "watch": "watch",
        "high": "overfitting",
    }.get(overfit_band, overfit_band)

    # Final Summary Output
    show_run_summary(best_loss, final_train_loss, final_val_loss, train_val_gap, overfit_warning)

    # Artifact saving
    save_run_artifacts(
        config=CONFIG,
        timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
        tokenizer=tokenizer,
        best_val_loss=best_loss,
        final_train_loss=final_train_loss,
        final_val_loss=final_val_loss,
        best_val_perplexity=math.exp(best_loss) if best_loss < 20 else float("inf"),
        final_train_perplexity=(
            math.exp(final_train_loss) if final_train_loss < 20 else float("inf")
        ),
        final_val_perplexity=math.exp(final_val_loss) if final_val_loss < 20 else float("inf"),
        sample_logs=trainer.sample_logs,
        model_type=CONFIG.model_type,
        project_data_path=CONFIG.data_path.resolve(),
        train_val_gap=train_val_gap,
        overfit_warning=overfit_warning,
        train_tokens=len(token_split.train_tokens),
        val_tokens=len(token_split.val_tokens),
    )


if __name__ == "__main__":
    main()
