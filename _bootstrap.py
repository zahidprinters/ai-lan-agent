from __future__ import annotations

import sys
from pathlib import Path


def _configure_utf8_streams() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (TypeError, ValueError, OSError):
                pass


def ensure_repo_root() -> Path:
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    _configure_utf8_streams()
    return root
