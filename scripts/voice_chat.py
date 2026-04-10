from __future__ import annotations

import sys

import _bootstrap

_bootstrap.ensure_repo_root()

from scripts import launch


if __name__ == "__main__":
    sys.exit(launch.main(["--mode", "voice"]))
