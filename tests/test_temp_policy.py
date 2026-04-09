from debug_utils import sentinel
import os
from pathlib import Path


@sentinel
def test_no_temp_files_outside_temp() -> None:
    """Fail if any temp files are created outside the project temp/ folder."""
    root = Path(__file__).resolve().parents[1]
    temp_dir = root / "temp"
    forbidden = []
    # Scan for files or folders named 'tmp', 'temp', or 'pytest' outside temp/
    for dirpath_str, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_str)

        # Skip the project's own temp directory and its subdirectories
        if dirpath == temp_dir or temp_dir in dirpath.parents:
            continue

        # Skip internal system/library folders
        if any(p.name in {".venv", ".git"} for p in [dirpath] + list(dirpath.parents)):
            continue

        # Check subdirectories
        # We need to be careful NOT to flag the root "temp" folder if dirpath is root.
        for dname in dirnames[:]:  # Copy list to allow modification
            if dname.lower() in {"tmp", "temp", "pytest"}:
                full_path = dirpath / dname
                # If it's the official project temp folder, skip it
                if full_path == temp_dir:
                    continue

                forbidden.append(str(full_path))
                dirnames.remove(dname)

        # Check files
        for fname in filenames:
            if fname.lower() in {"tmp", "temp", "pytest"}:
                forbidden.append(str(dirpath / fname))

    assert not forbidden, f"Temp/test files outside temp/: {forbidden}"
