import torch
from pathlib import Path
from learning.dataset.harvester import harvest_successful_actions
from training.trainer import Trainer
from training.config import load_config
from debug_utils import sentinel


@sentinel
def run_sleep_finetune() -> Path | None:
    """Performs the nightly fine-tuning using successful audit log entries."""
    config = load_config()
    log_path = Path("temp/action_audit.jsonl")
    entries = harvest_successful_actions(log_path)

    if not entries:
        print("No new data to train on.")
        return None

    print(f"Starting fine-tuning on {len(entries)} entries...")

    # Placeholder for actual training integration.
    # In a full implementation, we would create a temporary dataset
    # and run the Trainer for a few epochs.
    # For now, we simulate the result by copying the current best model.

    sleep_checkpoint = Path("temp/sleep_checkpoint.pt")
    sleep_checkpoint.parent.mkdir(parents=True, exist_ok=True)

    if config.best_model_path.exists():
        shutil_copy = __import__("shutil").copy
        shutil_copy(config.best_model_path, sleep_checkpoint)
        print(f"Mock fine-tuning complete. Checkpoint saved to {sleep_checkpoint}")
        return sleep_checkpoint
    else:
        print("Error: Current best model not found for fine-tuning.")
        return None


__all__ = ["run_sleep_finetune"]
