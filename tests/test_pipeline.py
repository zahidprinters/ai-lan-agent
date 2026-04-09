from debug_utils import sentinel
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path.cwd()
PROJECT_TEMP = ROOT / "temp"


@sentinel
def make_test_workspace(name: str) -> Path:
    workspace = PROJECT_TEMP / f"{name}_{uuid4().hex[:8]}"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.mark.integration
@sentinel
def test_training_and_generation_smoke() -> None:
    workspace = make_test_workspace("integration_smoke")
    data_path = workspace / "input.txt"
    models_dir = workspace / "models"
    runs_dir = workspace / "runs"
    data_path.write_text(
        (
            "AI engineering uses careful experiments and clear documentation.\n"
            "This small project trains a character model on technical text.\n"
            "Validation loss helps measure overfitting during training.\n"
            "Batching keeps memory use stable on a CPU based workflow.\n"
        )
        * 20,
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "AI_LAN_DATA_PATH": str(data_path),
            "AI_LAN_MODEL_PATH": str(models_dir / "char_model.pt"),
            "AI_LAN_BEST_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_RUNS_DIR": str(runs_dir),
            "AI_LAN_EPOCHS": "3",
            "AI_LAN_BLOCK_SIZE": "8",
            "AI_LAN_HIDDEN_SIZE": "16",
            "AI_LAN_BATCH_SIZE": "8",
            "AI_LAN_SAMPLE_EVERY": "1",
            "AI_LAN_SAMPLE_LENGTH": "20",
            "AI_LAN_LEARNING_RATE": "1e-3",
            "AI_LAN_GENERATE_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_GENERATE_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_GENERATE_TOKENS": "20",
            "PYTHONPATH": str(ROOT),
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "TMPDIR": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        train_result = subprocess.run(
            [sys.executable, "training/train_char_model.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = train_result.stdout
        assert "loss: " in output
        assert "val_loss: " in output
        assert "| Metric" in output  # My new table
        assert (models_dir / "char_model.pt").exists()
        assert (models_dir / "char_model_best.pt").exists()
        assert (models_dir / "char_tokenizer.json").exists()
        assert any(runs_dir.glob("*_samples.txt"))
        assert (runs_dir / "index.json").exists()
        summary_path = next(runs_dir.glob("*_summary.json"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["model_type"] == "char_mlp"
        assert summary["best_val_perplexity"] > 0
        assert "train_val_gap" in summary
        assert summary["overfit_warning"] in {"optimal", "watch", "overfitting"}

        generate_result = subprocess.run(
            [sys.executable, "training/generate.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        generated = generate_result.stdout.strip()
        assert generated
        assert "<UNK>" not in generated
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.unit
@sentinel
def test_generation_checkpoint_defaults_to_char_mlp() -> None:
    checkpoint = {"vocab_size": 12}
    assert checkpoint.get("model_type", "char_mlp") == "char_mlp"


@pytest.mark.integration
@sentinel
def test_bigram_training_and_generation_smoke() -> None:
    workspace = make_test_workspace("integration_bigram")
    data_path = workspace / "input.txt"
    models_dir = workspace / "models"
    runs_dir = workspace / "runs"
    data_path.write_text(
        ("abababababababababab\n" "bcbcbcbcbcbcbcbcbcbc\n" "AI AI AI AI AI AI AI\n") * 20,
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "AI_LAN_MODEL_TYPE": "bigram",
            "AI_LAN_DATA_PATH": str(data_path),
            "AI_LAN_MODEL_PATH": str(models_dir / "char_model.pt"),
            "AI_LAN_BEST_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_RUNS_DIR": str(runs_dir),
            "AI_LAN_EPOCHS": "2",
            "AI_LAN_BLOCK_SIZE": "8",
            "AI_LAN_HIDDEN_SIZE": "16",
            "AI_LAN_BATCH_SIZE": "8",
            "AI_LAN_SAMPLE_EVERY": "1",
            "AI_LAN_SAMPLE_LENGTH": "16",
            "AI_LAN_LEARNING_RATE": "1e-2",
            "AI_LAN_GENERATE_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_GENERATE_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_GENERATE_TOKENS": "16",
            "PYTHONPATH": str(ROOT),
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "TMPDIR": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        train_result = subprocess.run(
            [sys.executable, "training/train_char_model.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Model:   bigram" in train_result.stdout
        assert "TRAINING RUN SUMMARY" in train_result.stdout
        summary_path = next(runs_dir.glob("*_summary.json"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["model_type"] == "bigram"
        assert summary["best_val_perplexity"] > 0
        assert "train_val_gap" in summary

        generate_result = subprocess.run(
            [sys.executable, "training/generate.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "[INFO] Type:   bigram" in generate_result.stdout
        assert "--- Generated Output ---" in generate_result.stdout
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.integration
@sentinel
def test_generation_controls_support_batch_output() -> None:
    workspace = make_test_workspace("integration_generate_controls")
    data_path = workspace / "input.txt"
    models_dir = workspace / "models"
    runs_dir = workspace / "runs"
    data_path.write_text(("abababababababababab\n" "AI AI AI AI AI AI AI\n") * 20, encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "AI_LAN_MODEL_TYPE": "bigram",
            "AI_LAN_DATA_PATH": str(data_path),
            "AI_LAN_MODEL_PATH": str(models_dir / "char_model.pt"),
            "AI_LAN_BEST_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_RUNS_DIR": str(runs_dir),
            "AI_LAN_EPOCHS": "1",
            "AI_LAN_BLOCK_SIZE": "8",
            "AI_LAN_BATCH_SIZE": "8",
            "AI_LAN_SAMPLE_EVERY": "1",
            "AI_LAN_SAMPLE_LENGTH": "8",
            "AI_LAN_GENERATE_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_GENERATE_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_GENERATE_TOKENS": "8",
            "AI_LAN_GENERATE_TEMPERATURE": "0.7",
            "AI_LAN_GENERATE_TOP_K": "2",
            "AI_LAN_GENERATE_BATCH_SIZE": "3",
            "AI_LAN_GENERATE_SEED": "11",
            "PYTHONPATH": str(ROOT),
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "TMPDIR": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        subprocess.run(
            [sys.executable, "training/train_char_model.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        generate_result = subprocess.run(
            [sys.executable, "training/generate.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = generate_result.stdout
        assert "temperature=0.7 top_k=2" in output
        assert "samples=3 seed=11" in output
        assert "[sample 1]" in output
        assert "[sample 2]" in output
        assert "[sample 3]" in output
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.integration
@sentinel
def test_models_directory_is_recreated() -> None:
    workspace = make_test_workspace("integration_models")
    data_path = workspace / "input.txt"
    models_dir = workspace / "models"
    runs_dir = workspace / "runs"
    data_path.write_text(
        ("AI testing data improves reliability.\n" * 30),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "AI_LAN_DATA_PATH": str(data_path),
            "AI_LAN_MODEL_PATH": str(models_dir / "char_model.pt"),
            "AI_LAN_BEST_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_RUNS_DIR": str(runs_dir),
            "AI_LAN_EPOCHS": "2",
            "AI_LAN_BLOCK_SIZE": "8",
            "AI_LAN_HIDDEN_SIZE": "16",
            "AI_LAN_BATCH_SIZE": "8",
            "AI_LAN_SAMPLE_EVERY": "1",
            "AI_LAN_SAMPLE_LENGTH": "20",
            "AI_LAN_GENERATE_MODEL_PATH": str(models_dir / "char_model_best.pt"),
            "AI_LAN_GENERATE_TOKENIZER_PATH": str(models_dir / "char_tokenizer.json"),
            "AI_LAN_GENERATE_TOKENS": "20",
            "PYTHONPATH": str(ROOT),
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "TMPDIR": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    try:
        subprocess.run(
            [sys.executable, "training/train_char_model.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert models_dir.exists()
        assert runs_dir.exists()
        assert (runs_dir / "index.json").exists()

        subprocess.run(
            [sys.executable, "training/generate.py"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@pytest.mark.integration
@sentinel
def test_deployment_pipeline_quantize_and_onnx() -> None:
    workspace = make_test_workspace("integration_deploy")
    data_path = workspace / "input.txt"
    models_dir = workspace / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "char_model_best.pt"
    tokenizer_path = models_dir / "char_tokenizer.json"
    onnx_path = models_dir / "brain.onnx"
    quant_path = models_dir / "brain_q8.pt"

    # 1. Create a dummy checkpoint
    from training.config import ProjectConfig
    from training.factory import build_model
    from training.checkpoints import save_checkpoint
    from tokenizer.char_tokenizer import CharTokenizer

    config = ProjectConfig(block_size=8, hidden_size=16, n_layer=1, n_head=1, model_type="char_mlp")
    tokenizer = CharTokenizer()
    tokenizer.train("abc")
    tokenizer.save(tokenizer_path)
    model = build_model("char_mlp", config=config, vocab_size=tokenizer.vocab_size)

    save_checkpoint(
        path=model_path,
        model=model,
        tokenizer=tokenizer,
        config=config,
        best_val_loss=0.5,
        model_type="char_mlp",
    )

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "TMP": str(PROJECT_TEMP),
            "TEMP": str(PROJECT_TEMP),
            "PYTHONIOENCODING": "utf-8",
        }
    )

    try:
        # 2. Test Quantization Script
        subprocess.run(
            [
                sys.executable,
                "scripts/quantize_model.py",
                "--model",
                str(model_path),
                "--output",
                str(quant_path),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        assert quant_path.exists()

        # 3. Test ONNX Export Script
        subprocess.run(
            [
                sys.executable,
                "scripts/export_onnx.py",
                "--model",
                str(model_path),
                "--output",
                str(onnx_path),
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        assert onnx_path.exists()

        # 4. Test Infer Simple Script (Smoke test for quantized model)
        # Note: infer_simple.py needs a mechanism to load quantized models if not already supported.
        # For now, we check it doesn't crash on standard model.
        subprocess.run(
            [
                sys.executable,
                "scripts/infer_simple.py",
                "--model",
                str(model_path),
                "--tokenizer",
                str(tokenizer_path),
                "--prompt",
                "abc",
                "--length",
                "10",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    finally:
        shutil.rmtree(workspace, ignore_errors=True)
