from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
"""
Quantization Utility for AI Lan Models.
This script reduces the memory footprint and increases the inference speed of 
StackTransformer models by converting Linear layers to 8-bit integer precision.
"""

import torch
import argparse
import sys
import warnings
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.config import load_config, ProjectConfig
from training.checkpoints import load_checkpoint, load_model_from_checkpoint


@sentinel
def quantize_model(model_path: Path, quantized_path: Path, config: ProjectConfig) -> None:
    """
    Applies dynamic 8-bit quantization to a trained model.

    Args:
        model_path (Path): Path to the source .pt model checkpoint.
        quantized_path (Path): Destination path for the quantized checkpoint.
        config (ProjectConfig): Training configuration (fallback).
    """
    print(f"--- QUANTIZATION START ---")
    print(f"  Source: {model_path}")

    # Load model and state
    checkpoint = load_checkpoint(model_path)
    try:
        model, config, _ = load_model_from_checkpoint(
            checkpoint, fallback_config=config, allow_quantized=False
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    # Quantize
    print(f"  Applying dynamic quantization to Linear layers...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )

    # Prepare and save quantized state
    save_state = {
        "model_state": quantized_model.state_dict(),
        "model_type": checkpoint.get("model_type", config.model_type),
        "tokenizer": checkpoint.get("tokenizer", {}),
        "config": checkpoint.get("config", config.__dict__),
        "is_quantized": True,
    }

    torch.save(save_state, quantized_path)
    print(f"--- SUCCESS: Quantized model saved to {quantized_path} ---")


def main() -> None:
    """Main CLI entry point for model quantization."""
    parser = argparse.ArgumentParser(
        description="AI Lan Model Quantizer (8-bit)",
        epilog="""
Usage Examples:
  python scripts/quantize_model.py --model models/char_model_best.pt
  python scripts/quantize_model.py --model runs/2026_summary/checkpoint.pt --output deploy/brain_q8.pt
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Path to the source PyTorch checkpoint (.pt). Defaults to the project's best model.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Destination path for the quantized .pt file. Defaults to common naming conventions (stem_quantized.pt).",
    )

    args = parser.parse_args()

    config = load_config()
    model_raw_path = Path(args.model) if args.model else config.best_model_path
    output_path = (
        Path(args.output)
        if args.output
        else model_raw_path.with_name(model_raw_path.stem + "_quantized.pt")
    )

    if not model_raw_path.exists():
        print(f"[ERROR] Source checkpoint not found at: {model_raw_path}")
        print("   Please ensure you have completed at least one training run (Action 3).")
        sys.exit(1)

    quantize_model(model_raw_path, output_path, config)


if __name__ == "__main__":
    main()
