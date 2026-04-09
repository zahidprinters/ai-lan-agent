from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to path
import _bootstrap
_bootstrap.ensure_repo_root()

from scripts import launch

if __name__ == "__main__":
    sys.exit(launch.main(["--mode", "web"]))
