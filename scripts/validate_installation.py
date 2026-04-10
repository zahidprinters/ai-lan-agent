# Copyright (c) 2026 Nadeem Abbas
"""
System Validation Utility for AI Lan.
Verifies that all core dependencies, hardware acceleration (CUDA/MPS),
and model backends (PyTorch/ONNX) are correctly installed and functional.

Pass --phase4 to also validate the optional Phase 4 stack
(Playwright, Tavily, Tesseract, ADB, scrcpy).
"""

import sys
import shutil
import argparse
import torch
import platform
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()


def print_result(check: str, success: bool, message: str) -> None:
    status = "OK" if success else "FAIL"
    print(f" [{status}] {check.ljust(25)} : {message}")


def validate_phase4() -> int:
    """Validate optional Phase 4 tool stack."""
    print("AI Lan Phase 4 Tool Validator")
    print("=" * 50)
    failures = 0

    # Playwright
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]
        import playwright
        print_result("Playwright", True, f"v{playwright.__version__}")
    except ImportError as exc:
        print_result("Playwright", False, str(exc))
        failures += 1

    # Tavily
    try:
        import tavily  # type: ignore[import-untyped]
        print_result("Tavily SDK", True, "installed")
    except ImportError as exc:
        print_result("Tavily SDK", False, str(exc))
        failures += 1

    # pytesseract
    try:
        import pytesseract  # type: ignore[import-untyped]
        print_result("pytesseract", True, "installed")
    except ImportError as exc:
        print_result("pytesseract", False, str(exc))
        failures += 1

    # Tesseract binary
    tess_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    tess_on_path = shutil.which("tesseract")
    tess_file: str | None = next((p for p in tess_paths if Path(p).exists()), None)
    if tess_on_path or tess_file:
        loc = tess_on_path or tess_file
        print_result("Tesseract binary", True, str(loc))
    else:
        print_result("Tesseract binary", False, "not found on PATH or default install path")
        failures += 1

    # ADB
    adb_loc = shutil.which("adb")
    if adb_loc:
        print_result("adb", True, adb_loc)
    else:
        print_result("adb", False, "not found on PATH — run: winget install --id Google.PlatformTools")
        failures += 1

    # scrcpy
    scrcpy_loc = shutil.which("scrcpy")
    if scrcpy_loc:
        print_result("scrcpy", True, scrcpy_loc)
    else:
        print_result("scrcpy", False, "not found on PATH — run: winget install --id Genymobile.scrcpy")
        failures += 1

    print("=" * 50)
    if failures == 0:
        print("[SUCCESS] All Phase 4 tools are installed and ready.")
    else:
        print(f"[WARN] {failures} Phase 4 tool(s) missing. See above.")
    return 0 if failures == 0 else 1


def validate() -> int:
    print("AI Lan Installation Validator v0.3.0")
    print(f"=" * 50)
    print(f"OS Platform      : {platform.system()} {platform.release()}")
    print(f"Python Version   : {sys.version.split()[0]}")

    # 1. PyTorch Check
    torch_success = torch.__version__ is not None
    print_result("PyTorch Version", torch_success, f"v{torch.__version__}")

    # 2. Hardware Acceleration Check
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"

    print_result("Hardware Device", True, f"'{device}'")

    # 3. Core Dependencies Check
    try:
        import tokenizers  # type: ignore[import-untyped]
        import numpy as np

        print_result(
            "Core Libraries", True, f"tokenizers v{tokenizers.__version__}, numpy v{np.__version__}"
        )
        core_libraries_success = True
    except ImportError as e:
        print_result("Core Libraries", False, f"Missing: {str(e)}")
        core_libraries_success = False

    # 4. ONNX Tooling Check (Deployment Pillar)
    try:
        import onnx
        import onnxruntime as ort  # type: ignore[import-untyped]

        print_result(
            "ONNX Tooling", True, f"onnx v{onnx.__version__}, onnxruntime v{ort.__version__}"
        )
        onnx_tooling_success = True
    except ImportError:
        print_result(
            "ONNX Tooling",
            False,
            "onnx and/or onnxruntime missing (required for ONNX export/inference)",
        )
        onnx_tooling_success = False

    # 5. Tracking Tools Check (Experiment Pillar)
    try:
        import wandb  # type: ignore[import-not-found]
        import mlflow  # type: ignore[import-not-found]

        print_result("Tracking Tools", True, "Both Available (WandB & MLflow)")
    except ImportError:
        print_result("Tracking Tools", True, "Optional tracking tools missing (OK)")

    # 6. Workspace Integrity Check
    critical_dirs = ["data", "models", "training", "tokenizer", "docs"]
    missing = [d for d in critical_dirs if not Path(d).exists()]
    if not missing:
        print_result("Workspace Integrity", True, "All critical folders found")
    else:
        print_result("Workspace Integrity", False, f"Missing: {', '.join(missing)}")
    workspace_success = not missing

    print(f"=" * 50)
    if torch_success and core_libraries_success and onnx_tooling_success and workspace_success:
        print("[SUCCESS] AI Lan environment is ready for Phase 4.0!")
        return 0
    else:
        print("[ERROR] Critical dependencies missing. Run 'Action 1: Setup Environment'.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Lan installation validator")
    parser.add_argument("--phase4", action="store_true", help="Validate optional Phase 4 stack")
    args = parser.parse_args()

    if args.phase4:
        raise SystemExit(validate_phase4())
    raise SystemExit(validate())
