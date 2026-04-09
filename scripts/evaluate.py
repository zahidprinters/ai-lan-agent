from __future__ import annotations
import math
import torch
import torch.nn as nn
import argparse
import sys
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.config import load_config, ProjectConfig
from training.checkpoints import (
    load_checkpoint,
    load_config_from_checkpoint,
    load_model_from_checkpoint,
)
from training.dataset import CharSequenceDataset
from torch.utils.data import DataLoader
from tokenizer.factory import load_tokenizer
from training.inference import sample_text


@sentinel
def evaluate_model(
    model_path: Path,
    tokenizer_path: Path | None,
    data_path: Path | None,
    config: ProjectConfig,
) -> None:
    """
    Evaluates a model's linguistic performance on a specific dataset.

    Args:
        model_path (Path): Path to the source .pt checkpoint.
        tokenizer_path (Path): Path to the tokenizer metadata (.json or .pt).
        data_path (Path): Path to the evaluation text file (.txt).
        config (ProjectConfig): Experiment configuration.
    """
    print(f"--- EVALUATION START ---")
    print(f"  Model:     {model_path.name}")
    print(f"  Data:      {(data_path.name if data_path else 'auto')}")

    # Load and setup
    checkpoint = load_checkpoint(model_path)
    checkpoint_config = load_config_from_checkpoint(checkpoint, fallback=config)
    if data_path is not None:
        if not data_path.exists():
            print(f"⚠️ [WARN] Data file not found: {data_path}")
            return
        resolved_data_path = data_path
    else:
        resolved_data_path = (
            checkpoint_config.data_path
            if checkpoint_config.data_path.exists()
            else config.data_path
        )

    if tokenizer_path is not None:
        if not tokenizer_path.exists():
            raise FileNotFoundError(f"Tokenizer file not found: {tokenizer_path}")
        resolved_tokenizer_path = tokenizer_path
    else:
        resolved_tokenizer_path = (
            checkpoint_config.tokenizer_path
            if checkpoint_config.tokenizer_path.exists()
            else config.tokenizer_path
        )
    tokenizer = load_tokenizer(resolved_tokenizer_path)

    model, checkpoint_config, _ = load_model_from_checkpoint(
        checkpoint,
        tokenizer_vocab_size=getattr(tokenizer, "vocab_size", None),
        fallback_config=config,
        allow_quantized=True,
    )

    # Prepare data
    if not resolved_data_path.exists():
        print(f"⚠️ [WARN] Data file not found: {resolved_data_path}")
        return

    text = resolved_data_path.read_text(encoding="utf-8")
    tokens = tokenizer.encode(text)
    dataset = CharSequenceDataset(tokens, checkpoint_config.block_size)
    loader = DataLoader(dataset, batch_size=checkpoint_config.batch_size, shuffle=False)

    # Compute metrics
    total_loss: float = 0.0
    total_batches: int = 0
    loss_fn = nn.CrossEntropyLoss()

    print(f"  Computing metrics over {len(dataset)} sequences...")
    with torch.no_grad():
        for x_batch, y_batch in loader:
            logits = model(x_batch)
            if logits.dim() == 3:
                logits = logits[:, -1, :]
            loss: torch.Tensor = loss_fn(logits, y_batch)
            total_loss += loss.item()
            total_batches += 1

    avg_loss = total_loss / max(total_batches, 1)
    perplexity = math.exp(avg_loss) if avg_loss < 20 else float("inf")

    print("-" * 32)
    print(f"  📈 Evaluation Results:")
    print(f"  - Avg Loss:   {avg_loss:.4f}")
    print(f"  - Perplexity: {perplexity:.4f}")
    print("-" * 32)

    # Sample generation
    print(f"  Sample Generation (Temp 0.8):")
    sample = sample_text(
        model=model,
        tokenizer=tokenizer,
        start_text="The AI",
        length=100,
        block_size=checkpoint_config.block_size,
        temperature=0.8,
    )
    print(f"  '{sample}'")
    print(f"✅ [SUCCESS] Evaluation complete.")


def main() -> None:
    """Main CLI entry point for model evaluation."""
    parser = argparse.ArgumentParser(
        description="🚀 AI Lan Model Evaluator",
        epilog="""
Usage Examples:
  python scripts/evaluate.py --model models/char_model_best.pt
  python scripts/evaluate.py --model runs/2026_summary/checkpoint.pt --data data/eval.txt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Path to the source PyTorch checkpoint (.pt). Defaults to project's best model.",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to the evaluation text file (.txt). Defaults to training corpus.",
    )

    args = parser.parse_args()

    config = load_config()
    model_path = Path(args.model) if args.model else config.best_model_path
    if not model_path.exists():
        print(f"❌ [ERROR] Source checkpoint not found at: {model_path}")
        print("   Please ensure you have completed at least one training run (Action 3).")
        sys.exit(1)

    evaluate_model(model_path, None, Path(args.data) if args.data else None, config)


if __name__ == "__main__":
    main()
