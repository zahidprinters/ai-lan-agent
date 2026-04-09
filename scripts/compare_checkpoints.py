from datetime import datetime
from pathlib import Path

import torch

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()

from debug_utils import sentinel

MODELS_DIR = ROOT / "models"
DEFAULT_FILES = [
    MODELS_DIR / "char_model_best.pt",
    MODELS_DIR / "char_model.pt",
]


@sentinel
def format_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


@sentinel
def load_checkpoint(path: Path) -> dict:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "modified": format_timestamp(path),
        "model_type": checkpoint.get("model_type", "char_mlp"),
        "best_val_loss": checkpoint.get("best_val_loss", "n/a"),
        "best_val_perplexity": checkpoint.get("best_val_perplexity", "n/a"),
        "learning_rate": checkpoint.get("learning_rate", "n/a"),
        "batch_size": checkpoint.get("batch_size", "n/a"),
        "train_ratio": checkpoint.get("train_ratio", "n/a"),
        "block_size": checkpoint.get("block_size", "n/a"),
        "hidden_size": checkpoint.get("hidden_size", "n/a"),
        "vocab_size": checkpoint.get("vocab_size", "n/a"),
    }


@sentinel
def main() -> None:
    found = [path for path in DEFAULT_FILES if path.exists()]
    if not found:
        raise SystemExit("No checkpoint files found in models/ to compare.")

    print("AI Lan checkpoint comparison")
    print(f"models directory: {MODELS_DIR}")
    print()

    for path in found:
        summary = load_checkpoint(path)
        print(path.name)
        for key, value in summary.items():
            if key == "path":
                continue
            print(f"  {key}: {value}")
        print()


if __name__ == "__main__":
    main()
