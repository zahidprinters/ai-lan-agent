from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
"""
ONNX Export Utility for AI Lan.
Converts trained PyTorch models into the ONNX (Open Neural Network Exchange) 
format for ultra-fast, cross-platform CPU and edge-device inference.
"""

import json
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
def _write_onnx_metadata(
    onnx_path: Path,
    *,
    source_checkpoint: Path,
    checkpoint: dict[str, object],
    config: ProjectConfig,
    vocab_size: int,
) -> None:
    meta_path = onnx_path.with_suffix(".meta.json")
    meta = {
        "model_type": str(checkpoint.get("model_type", config.model_type)),
        "block_size": config.block_size,
        "hidden_size": config.hidden_size,
        "vocab_size": vocab_size,
        "tokenizer_path": str(getattr(config, "tokenizer_path", "")),
        "generate_tokenizer_path": str(getattr(config, "generate_tokenizer_path", "")),
        "n_layer": getattr(config, "n_layer", 0),
        "n_head": getattr(config, "n_head", 0),
        "dropout": getattr(config, "dropout", 0.0),
        "stochastic_depth": getattr(config, "stochastic_depth", 0.0),
        "source_checkpoint": str(source_checkpoint),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=True), encoding="utf-8")


@sentinel
def export_onnx(model_path: Path, onnx_path: Path, config: ProjectConfig) -> None:
    """
    Traces and exports a trained model to ONNX format.

    Args:
        model_path (Path): Source .pt checkpoint.
        onnx_path (Path): Destination .onnx file path.
        config (ProjectConfig): Architecture configuration (fallback).
    """
    print(f"--- ONNX EXPORT START ---")
    print(f"  Source: {model_path}")

    try:
        import onnx  # noqa: F401
    except ImportError:
        print("❌ [ERROR] The 'onnx' package is required for ONNX export. Install it and retry.")
        sys.exit(1)

    # Load and setup model
    checkpoint = load_checkpoint(model_path)
    try:
        model, config, vocab_size = load_model_from_checkpoint(
            checkpoint,
            fallback_config=config,
            allow_quantized=False,
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    # Create dummy input for tracing (batch=1, context=block_size)
    dummy_input = torch.randint(0, vocab_size, (1, config.block_size), dtype=torch.long)

    # Export
    print(f"  Tracing model graph with dummy input...")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            torch.onnx.export(
                model,
                (dummy_input,),
                str(onnx_path),
                export_params=True,
                opset_version=14,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
                dynamo=False,
            )
        _write_onnx_metadata(
            onnx_path,
            source_checkpoint=model_path,
            checkpoint=checkpoint,
            config=config,
            vocab_size=vocab_size,
        )
        print(f"--- SUCCESS: ONNX model exported to {onnx_path} ---")
    except Exception as e:
        print(f"[ERROR] ONNX export failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point for ONNX export."""
    parser = argparse.ArgumentParser(
        description="AI Lan ONNX Exporter",
        epilog="""
Usage Examples:
  python scripts/export_onnx.py --model models/char_model_best.pt
  python scripts/export_onnx.py --model runs/2026_summary/checkpoint.pt --output deploy/brain.onnx
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
        help="Destination path for the exported .onnx file. Defaults to the source path with a .onnx extension.",
    )

    args = parser.parse_args()

    config = load_config()
    model_raw_path = Path(args.model) if args.model else config.best_model_path
    output_path = Path(args.output) if args.output else model_raw_path.with_suffix(".onnx")

    if not model_raw_path.exists():
        print(f"[ERROR] Source checkpoint not found at: {model_raw_path}")
        print("   Please ensure you have completed at least one training run (Action 3).")
        sys.exit(1)

    export_onnx(model_raw_path, output_path, config)


if __name__ == "__main__":
    main()
