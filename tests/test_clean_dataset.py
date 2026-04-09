from debug_utils import sentinel
import subprocess
import sys
from pathlib import Path
import tempfile


@sentinel
def test_clean_dataset_removes_empty_and_duplicates(tmp_path: Path) -> None:
    # Prepare a test input file
    input_lines = ["alpha\n", "\n", "beta\n", "alpha\n", "  gamma  \n", "\n", "beta\n", "delta\n"]
    input_path = tmp_path / "input.txt"
    input_path.write_text("".join(input_lines), encoding="utf-8")
    output_path = tmp_path / "input_cleaned.txt"

    # Run the cleaning script
    result = subprocess.run(
        [
            sys.executable,
            "scripts/clean_dataset.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )
    cleaned = output_path.read_text(encoding="utf-8").splitlines()
    # Should remove empty lines and duplicates, and strip whitespace
    assert cleaned == ["alpha", "beta", "gamma", "delta"]
    assert "Original lines: 8" in result.stdout
    assert "Cleaned lines: 4" in result.stdout
