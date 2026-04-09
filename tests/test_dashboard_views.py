from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["models"], ["Model Registry", "Record count", "Records"]),
        (["context", "--query", "system status"], ["Context Assembly", "Assembled context"]),
        (["logs"], ["Logs", "Audit entries", "Error lines", "Legacy action lines"]),
        (["ops"], ["System Control", "Commands", "Paths"]),
    ],
)
def test_dashboard_views_render_local_sections(args: list[str], expected: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/dashboard_views.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    for token in expected:
        assert token in result.stdout
