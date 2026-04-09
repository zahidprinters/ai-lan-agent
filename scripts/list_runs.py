import argparse

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.checkpoints import build_sorted_summaries
from training.config import load_config


@sentinel
def _display(value: object) -> object:
    return "n/a" if value is None else value


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show the AI Lan experiment leaderboard.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all recorded runs, including external or legacy runs.",
    )
    return parser.parse_args()


@sentinel
def main() -> None:
    args = parse_args()
    config = load_config()
    summaries = build_sorted_summaries(config.runs_dir, config.data_path.resolve())
    if not summaries:
        raise SystemExit(f"No run summaries found in {config.runs_dir}.")

    index_path = config.run_all_index_path if args.all else config.run_index_path
    scope = "all runs" if args.all else "project runs"
    project_summaries = [item for item in summaries if item.get("is_project_run")]
    visible_summaries = summaries if args.all or not project_summaries else project_summaries

    print("AI Lan experiment leaderboard")
    print(f"scope: {scope}")
    print(f"index: {index_path}")
    print()

    for rank, entry in enumerate(visible_summaries[:10], start=1):
        run_type = "project" if entry.get("is_project_run") else "external"
        print(f"#{rank} {entry['summary_file']} [{run_type}]")
        print(f"  model_type: {entry.get('model_type', 'char_mlp')}")
        print(f"  best_val_loss: {_display(entry.get('best_val_loss'))}")
        print(f"  best_val_perplexity: {_display(entry.get('best_val_perplexity'))}")
        print(f"  final_train_loss: {_display(entry.get('final_train_loss'))}")
        print(f"  final_val_loss: {_display(entry.get('final_val_loss'))}")
        print(f"  final_train_perplexity: {_display(entry.get('final_train_perplexity'))}")
        print(f"  final_val_perplexity: {_display(entry.get('final_val_perplexity'))}")
        print(f"  train_val_gap: {_display(entry.get('train_val_gap'))}")
        print(f"  overfit_warning: {_display(entry.get('overfit_warning'))}")
        print(f"  learning_rate: {_display(entry.get('learning_rate'))}")
        print(f"  batch_size: {_display(entry.get('batch_size'))}")
        print(f"  block_size: {_display(entry.get('block_size'))}")
        print(f"  hidden_size: {_display(entry.get('hidden_size'))}")
        print(f"  data_path: {_display(entry.get('data_path'))}")
        print()


if __name__ == "__main__":
    main()
