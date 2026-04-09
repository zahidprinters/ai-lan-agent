import json
import torch
import argparse
import sys
from pathlib import Path
from typing import Any

from _bootstrap import ensure_repo_root

ensure_repo_root()

from debug_utils import sentinel
from training.config import load_config
from training.inference import sample_text
from training.checkpoints import (
    load_checkpoint,
    load_config_from_checkpoint,
    load_model_from_checkpoint,
)
from tokenizer.factory import load_tokenizer


@sentinel
def _load_onnx_metadata(onnx_path: Path) -> dict[str, object]:
    meta_path = onnx_path.with_suffix(".meta.json")
    if not meta_path.exists():
        return {}
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


@sentinel
def _resolve_tokenizer_path(
    preferred: Path | None, *, checkpoint_config: Any, fallback_config: Any
) -> Path:
    def _candidate_path(source: Any, key: str) -> Path | None:
        value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value:
            return Path(value)
        return None

    if preferred is not None and preferred.exists():
        return preferred
    if preferred is not None:
        raise FileNotFoundError(f"Tokenizer file not found: {preferred}")

    for candidate in (
        _candidate_path(checkpoint_config, "generate_tokenizer_path"),
        _candidate_path(checkpoint_config, "tokenizer_path"),
        _candidate_path(fallback_config, "generate_tokenizer_path"),
        _candidate_path(fallback_config, "tokenizer_path"),
    ):
        if candidate is not None and candidate.exists():
            return candidate

    candidate = _candidate_path(checkpoint_config, "tokenizer_path")
    if candidate is not None:
        return candidate
    candidate = _candidate_path(fallback_config, "tokenizer_path")
    if candidate is not None:
        return candidate
    raise FileNotFoundError("Unable to resolve a tokenizer path for inference.")


@sentinel
def run_onnx_inference(
    onnx_path: Path, tokenizer_path: Path | None, prompt: str, length: int
) -> None:
    """
    Performs high-performance inference using the ONNX Runtime backend.

    Note: This ONNX path intentionally uses greedy argmax decoding for
    portability and reproducibility. It does not apply temperature/top-k/top-p.
    """
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
        import numpy as np
    except ImportError:
        print("❌ [ERROR] onnxruntime not found. Please install it to use ONNX inference.")
        sys.exit(1)

    print(f"--- ONNX INFERENCE START ---")
    config = load_config()
    metadata = _load_onnx_metadata(onnx_path)
    resolved_tokenizer_path = _resolve_tokenizer_path(
        tokenizer_path, checkpoint_config=metadata or {}, fallback_config=config
    )
    tokenizer = load_tokenizer(resolved_tokenizer_path)
    block_size = (
        int(str(metadata.get("block_size", config.block_size))) if metadata else config.block_size
    )

    # Setup session
    session = ort.InferenceSession(str(onnx_path))

    input_tokens = tokenizer.encode(prompt)
    if not input_tokens:
        input_tokens = [0]

    context = input_tokens.copy()
    print(f"  Backend:    ONNX Runtime (CPU)")
    print(f"  Prompt:     '{prompt}'")
    print("-" * 32)

    # Simple Greedy/Top-K generation for ONNX (Standalone logic)
    for _ in range(length):
        window = context[-block_size:]
        if len(window) < block_size:
            window = [0] * (block_size - len(window)) + window

        # ONNX input must be numpy
        x = np.array([window], dtype=np.int64)
        outputs = session.run(None, {"input": x})
        logits = outputs[0][0][-1]  # Get last token logits

        # Simple greedy for demo (could be expanded)
        next_token = int(np.argmax(logits))
        context.append(next_token)

    print(tokenizer.decode(context))
    print("-" * 32)
    print(f"--- SUCCESS: ONNX Generation finished ---")


@sentinel
def run_standalone_inference(
    model_path: Path, tokenizer_path: Path | None, prompt: str, length: int
) -> None:
    """
    Performs standard PyTorch inference on a .pt checkpoint.
    """
    print(f"--- PYTORCH INFERENCE START ---")

    # Load model and state
    runtime_config = load_config()
    checkpoint = load_checkpoint(model_path)
    checkpoint_config = load_config_from_checkpoint(checkpoint, fallback=runtime_config)
    resolved_tokenizer_path = _resolve_tokenizer_path(
        tokenizer_path,
        checkpoint_config=checkpoint_config,
        fallback_config=runtime_config,
    )
    # Load tokenizer
    tokenizer = load_tokenizer(resolved_tokenizer_path)
    model, config, _ = load_model_from_checkpoint(
        checkpoint,
        tokenizer_vocab_size=getattr(tokenizer, "vocab_size", None),
        fallback_config=checkpoint_config,
        allow_quantized=True,
    )

    print(f"  Backend:    PyTorch ({'Quantized' if checkpoint.get('is_quantized') else 'Full'})")
    print(f"  Model Type: {checkpoint.get('model_type', config.model_type)}")
    print(f"  Prompt:     '{prompt}'")
    print("-" * 32)

    # Generate
    result = sample_text(
        model=model,
        tokenizer=tokenizer,
        start_text=prompt,
        length=length,
        block_size=config.block_size,
        temperature=0.8,
        top_k=40,
    )

    print(result)
    print("-" * 32)
    print(f"--- SUCCESS: PyTorch Generation finished ---")


def main() -> None:
    """Main CLI entry point for standalone inference."""
    parser = argparse.ArgumentParser(
        description="AI Lan Standalone Inference (Multi-Backend)",
        epilog="""
Usage Examples:
  # PyTorch (.pt) Inference
  python scripts/infer_simple.py --model models/char_model_best.pt --prompt "The galaxy is"
  
  # ONNX Runtime (.onnx) Inference
  python scripts/infer_simple.py --model deploy/brain.onnx --prompt "Artificial Intelligence" --length 200
  
  # Configuration Overrides
  AI_LAN_DEVICE='cuda' python scripts/infer_simple.py --prompt "GPU accelerated generation"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", type=str, help="Model path (.pt or .onnx). Defaults to project best model."
    )
    parser.add_argument(
        "--tokenizer",
        type=str,
        help="Tokenizer metadata path (.json/.pt). Defaults to project tokenizer.",
    )
    parser.add_argument("--prompt", type=str, default="AI", help="Inference prompt text.")
    parser.add_argument("--length", type=int, default=100, help="Number of tokens to generate.")

    args = parser.parse_args()
    config = load_config()

    model_path = Path(args.model) if args.model else config.best_model_path
    tokenizer_path = Path(args.tokenizer) if args.tokenizer else None

    if not model_path.exists():
        print(f"[ERROR] Model not found at: {model_path}")
        sys.exit(1)

    if model_path.suffix == ".onnx":
        run_onnx_inference(model_path, tokenizer_path, args.prompt, args.length)
    else:
        run_standalone_inference(model_path, tokenizer_path, args.prompt, args.length)


if __name__ == "__main__":
    main()
