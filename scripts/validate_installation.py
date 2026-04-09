# Copyright (c) 2026 Nadeem Abbas
"""
System Validation Utility for AI Lan.
Verifies that all core dependencies, hardware acceleration (CUDA/MPS),
and model backends (PyTorch/ONNX) are correctly installed and functional.
"""

import sys
import torch
import platform
from pathlib import Path

from _bootstrap import ensure_repo_root

ensure_repo_root()


def print_result(check: str, success: bool, message: str) -> None:
    status = "OK" if success else "FAIL"
    print(f" [{status}] {check.ljust(25)} : {message}")


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
    raise SystemExit(validate())
