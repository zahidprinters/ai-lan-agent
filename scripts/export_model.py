from __future__ import annotations

# Copyright (c) 2026 Nadeem Abbas
"""
Deployment Export Utility for AI Lan.
Provides functions to export model weights and tokenizer states for use in 
production environments or standalone inference scripts.
"""

import argparse
import sys
import torch
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.checkpoints import load_checkpoint, load_model_from_checkpoint
from tokenizer.factory import load_tokenizer


@sentinel
def export_model_weights(model_path: str, export_path: str) -> None:
    """
    Exports clean model weights (state_dict) by removing optimizer states
    and extra checkpoint metadata.

    Args:
        model_path (str): File path to source .pt checkpoint.
        export_path (str): Destination path for the exported .pt weights.
    """
    print(f"--- Model Export Start ---")
    print(f"  Source: {model_path}")

    # Load and map state
    checkpoint = load_checkpoint(Path(model_path))
    try:
        model, _, _ = load_model_from_checkpoint(checkpoint, allow_quantized=False)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    # Save clean weights
    torch.save(model.state_dict(), export_path)
    print(f"--- SUCCESS: Clean weights exported to {export_path} ---")


@sentinel
def export_tokenizer(tokenizer_path: str, export_path: str) -> None:
    """
    Exports a tokenizer file to a new location.

    Args:
        tokenizer_path (str): Source .json or .pt path.
        export_path (str): Export destination.
    """
    print(f"--- Tokenizer Export Start ---")
    src = Path(tokenizer_path)
    dest = Path(export_path)

    if not src.exists():
        print(f"[ERROR] Source tokenizer not found: {src}")
        return

    # Load to verify it's valid, then copy
    _ = load_tokenizer(src)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"--- SUCCESS: Tokenizer exported to {export_path} ---")


def main() -> None:
    """Main CLI entry point for model deployment export."""
    parser = argparse.ArgumentParser(
        description="📦 AI Lan Deployment Exporter",
        epilog="""
Usage Examples:
  # Export clean model weights
  python scripts/export_model.py --model models/char_model_best.pt --export deploy/weights.pt
  
  # Export tokenizer metadata
  python scripts/export_model.py --tokenizer models/tokenizer.json --export deploy/tokenizer.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", type=str, help="Source .pt model checkpoint to strip and export."
    )
    parser.add_argument(
        "--tokenizer", type=str, help="Source tokenizer metadata (.json or .pt) to export."
    )
    parser.add_argument(
        "--export", type=str, required=True, help="Destination file path for the exported artifact."
    )

    args = parser.parse_args()

    if args.model:
        export_model_weights(args.model, args.export)
    elif args.tokenizer:
        export_tokenizer(args.tokenizer, args.export)
    else:
        print("❌ [ERROR] You must specify either --model or --tokenizer as a source.")
        print("   Usage: python scripts/export_model.py --model <PATH> --export <DEST>")
        sys.exit(1)


if __name__ == "__main__":
    main()
