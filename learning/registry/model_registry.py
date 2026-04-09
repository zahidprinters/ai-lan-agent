import json
import shutil
from pathlib import Path
from datetime import datetime
from debug_utils import sentinel


@sentinel
def promote_model(new_model_path: Path, registry_path: Path, models_dir: Path):
    """Backs up the current best model and promotes a new one, updating the registry."""
    if not registry_path.exists():
        # Initialize if missing
        registry = {"current_version": 0, "history": []}
    else:
        with registry_path.open("r", encoding="utf-8") as f:
            registry = json.load(f)

    current_best = models_dir / "best_model.pt"
    new_version = registry["current_version"] + 1
    backups_dir = models_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    # Backup current best if it exists
    if current_best.exists():
        backup_path = backups_dir / f"best_model_v{registry['current_version']}.pt"
        shutil.copy(current_best, backup_path)

    # Overwrite best with new model
    shutil.copy(new_model_path, current_best)

    # Update registry
    registry["current_version"] = new_version
    registry["history"].append(
        {
            "version": new_version,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "path": "models/best_model.pt",
            "description": f"Sleep Mode auto-promotion v{new_version}",
        }
    )

    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


__all__ = ["promote_model"]
