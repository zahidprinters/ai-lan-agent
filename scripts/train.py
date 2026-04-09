"""Unified training entrypoint placeholder."""

from _bootstrap import ensure_repo_root

ensure_repo_root()

from training.train_char_model import main

if __name__ == "__main__":
    main()
