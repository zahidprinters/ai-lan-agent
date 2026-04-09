from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.checkpoints import update_run_index
from training.config import load_config


@sentinel
def main() -> None:
    config = load_config()
    update_run_index(config, config.data_path.resolve())
    print(f"updated visible project index: {config.run_index_path}")
    print(f"updated full run index: {config.run_all_index_path}")
    legacy_all_index = config.runs_dir / "all_index.json"
    if legacy_all_index != config.run_all_index_path:
        print(f"updated legacy full run index: {legacy_all_index}")


if __name__ == "__main__":
    main()
