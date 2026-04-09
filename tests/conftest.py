from pathlib import Path
import os
import sys
from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMP_DIR = ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)
os.environ["TMP"] = str(TEMP_DIR)
os.environ["TEMP"] = str(TEMP_DIR)
os.environ["TMPDIR"] = str(TEMP_DIR)


import pytest


@pytest.fixture(autouse=True)
def enable_sentinel() -> Iterator[None]:
    os.environ.setdefault("AI_LAN_DEBUG", "1")
    # Keep tracing/profile disabled by default to avoid global slowdown.
    os.environ.setdefault("AI_LAN_TRACE", "0")
    os.environ.setdefault("AI_LAN_PROFILE", "0")
    yield
