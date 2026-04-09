# tests/integration/test_deployment_integration.py
# Copyright (c) 2026 Nadeem Abbas
"""
Professional Integration Tests for AI Lan Deployment Pipelines.
Verifies ONNX export, 8-bit quantization, and standalone inference workflows.
"""

import os
import sys
import shutil
import importlib.util
import pytest
import subprocess
from pathlib import Path
from debug_utils import sentinel

ROOT = Path(__file__).parent.parent.parent
PROJECT_TEMP = ROOT / ".temp"


def make_test_workspace(name: str) -> Path:
    """Setup a dedicated test workspace."""
    workspace = PROJECT_TEMP / "integration" / name
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.mark.integration
@sentinel
def test_full_deployment_cycle_pt_to_onnx_to_quant() -> None:
    """
    Verifies that a model can successfully move from PT -> ONNX -> Quantization
    without regressing core functionality.
    """
    workspace = make_test_workspace("full_deploy_cycle")
    if importlib.util.find_spec("onnx") is None:
        pytest.skip("onnx is not installed; ONNX export is optional in this environment.")
    model_dir = workspace / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    src_pt = model_dir / "best.pt"
    out_onnx = model_dir / "model.onnx"
    out_quant = model_dir / "model_q8.pt"

    # Step 1: Create a valid dummy checkpoint
    from training.config import ProjectConfig
    from training.factory import build_model
    from training.checkpoints import save_checkpoint
    from tokenizer.char_tokenizer import CharTokenizer
    import torch

    # Use minimal config for speed
    config = ProjectConfig(block_size=8, hidden_size=16, n_layer=1, n_head=1)
    tokenizer = CharTokenizer()
    tokenizer.train("abcdefghijklmnopqrstuvwxyz")
    model = build_model("transformer", config=config, vocab_size=tokenizer.vocab_size)

    save_checkpoint(
        path=src_pt,
        model=model,
        tokenizer=tokenizer,
        config=config,
        best_val_loss=0.5,
        model_type="transformer",
    )

    # Step 2: Validate Environment
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "AI_LAN_DEBUG": "0",  # Disable noise
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )

    try:
        # Step 3: Run ONNX Export Script
        print(f"  [Integration] Testing ONNX Export...")
        subprocess.run(
            [
                sys.executable,
                "scripts/export_onnx.py",
                "--model",
                str(src_pt),
                "--output",
                str(out_onnx),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        assert out_onnx.exists(), "ONNX export failed to produce an artifact."

        # Step 4: Run Quantization Script
        print(f"  [Integration] Testing Quantization...")
        subprocess.run(
            [
                sys.executable,
                "scripts/quantize_model.py",
                "--model",
                str(src_pt),
                "--output",
                str(out_quant),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        assert out_quant.exists(), "Quantization failed to produce an artifact."

        # Step 5: Smoke Test Standalone Inference
        print(f"  [Integration] Testing Standalone Inference...")
        res = subprocess.run(
            [
                sys.executable,
                "scripts/infer_simple.py",
                "--model",
                str(src_pt),
                "--prompt",
                "abc",
                "--length",
                "5",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert len(res.stdout) > 0, "Standalone inference returned no output."
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__])
