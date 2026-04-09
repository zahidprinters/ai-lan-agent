import time
import sys
from datetime import datetime
from pathlib import Path
from debug_utils import sentinel

from learning.training.sleep_finetune import run_sleep_finetune
from learning.registry.model_registry import promote_model
from training.config import load_config


@sentinel
def main():
    """Main Sleep Mode scheduler."""
    config = load_config()
    print(f"--- AI Lan Sleep Mode Active ---")
    print(f"Scheduled fine-tuning hour: {config.sleep_mode_hour}:00")
    print(f"Auto-promotion: {'Enabled' if config.auto_promote else 'Disabled'}")

    while True:
        now = datetime.now()

        # Check if it's the scheduled hour
        if now.hour == config.sleep_mode_hour:
            print(f"\n[{now.isoformat()}] Starting scheduled Sleep Mode cycle...")

            # Step 1: Run fine-tuning
            new_model = run_sleep_finetune()

            # Step 2: Promote if successful and auto-promotion is enabled
            if new_model and config.auto_promote:
                registry_path = Path("models/model_registry.json")
                models_dir = Path("models")
                try:
                    promote_model(new_model, registry_path, models_dir)
                    print("Model promoted and registry updated.")
                except Exception as exc:
                    print(f"Error during model promotion: {exc}")

            # Step 3: Archive current audit logs to prevent re-processing
            log_path = Path("temp/action_audit.jsonl")
            if log_path.exists():
                archives_dir = Path("temp/archives")
                archives_dir.mkdir(parents=True, exist_ok=True)
                archive_filename = f"audit_{now.strftime('%Y%m%d_%H%M%S')}.jsonl"
                archive_path = archives_dir / archive_filename
                try:
                    log_path.rename(archive_path)
                    print(f"Audit log archived to {archive_path}")
                except Exception as exc:
                    print(f"Error archiving audit log: {exc}")

            print("Sleep Mode cycle complete. Waiting for next window...")
            # Wait for 1 hour + a buffer to ensure we don't trigger again in the same hour
            time.sleep(3660)

        # Sleep for 1 minute between checks
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSleep Mode terminated by user.")
        sys.exit(0)
