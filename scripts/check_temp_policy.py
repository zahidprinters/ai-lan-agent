import os
from pathlib import Path

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()

from debug_utils import sentinel


@sentinel
def check_no_temp_files_outside_temp() -> None:
    """Fail if any temp files are created outside the project temp/ folder."""
    temp_dir = ROOT / "temp"
    forbidden = []
    for dirpath_str, dirnames, filenames in os.walk(ROOT):
        dirpath = Path(dirpath_str)
        # Skip temp folder and .venv
        if temp_dir in dirpath.parents or dirpath == temp_dir or ".venv" in dirpath.parts:
            continue
        for name in dirnames + filenames:
            if name.lower() in {"tmp", "temp", "pytest"}:
                # If the folder itself is 'temp' and it's in the root, it's fine
                # But 'name' here is a child of 'dirpath'
                if dirpath == ROOT and name.lower() == "temp":
                    continue
                forbidden.append(str(dirpath / name))
    if forbidden:
        print(f"[ERROR] Temp/test files outside temp/: {forbidden}")
        exit(1)
    print("[OK] No temp/test files outside temp/")


if __name__ == "__main__":
    check_no_temp_files_outside_temp()
