from __future__ import annotations
from pathlib import Path

from _bootstrap import ensure_repo_root

ROOT = ensure_repo_root()

from debug_utils import sentinel, ensure_project_temp

# from project_temp import ensure_project_temp # DELETED
from tokenizer.factory import load_tokenizer
from training.checkpoints import (
    load_checkpoint,
    load_config_from_checkpoint,
    load_model_from_checkpoint,
)
from training.config import load_config
from training.inference import sample_texts

CONFIG = load_config()
TEMP_DIR = ensure_project_temp(ROOT)


@sentinel
def main() -> None:
    print("=" * 64)
    print("AI LAN - GENERATION MODULE")
    print("=" * 64)
    print(f"[INFO] Model:  {CONFIG.generate_model_path}")
    print(f"[INFO] Temp:   {TEMP_DIR}")
    print(f"[INFO] Seed:   {CONFIG.generate_start_text!r}")
    print(f"[INFO] TempK:  temperature={CONFIG.generate_temperature} top_k={CONFIG.generate_top_k}")
    print(f"[INFO] Batch:  samples={CONFIG.generate_batch_size} seed={CONFIG.generate_seed}")
    print("=" * 64)

    if not CONFIG.generate_model_path.exists():
        raise FileNotFoundError(f"Generation model not found: {CONFIG.generate_model_path}")

    checkpoint = load_checkpoint(CONFIG.generate_model_path)
    checkpoint_config = load_config_from_checkpoint(checkpoint, fallback=CONFIG)
    tokenizer_path = (
        checkpoint_config.generate_tokenizer_path
        if checkpoint_config.generate_tokenizer_path.exists()
        else checkpoint_config.tokenizer_path
    )
    if not tokenizer_path.exists():
        tokenizer_path = CONFIG.generate_tokenizer_path
    if not tokenizer_path.exists():
        raise FileNotFoundError(f"Generation tokenizer not found: {tokenizer_path}")
    print(f"[INFO] Token:  {tokenizer_path}")
    tokenizer = load_tokenizer(tokenizer_path)
    print(f"[INFO] Type:   {checkpoint.get('model_type', CONFIG.model_type)}")
    print("=" * 64)
    model, checkpoint_config, _ = load_model_from_checkpoint(
        checkpoint,
        tokenizer_vocab_size=getattr(tokenizer, "vocab_size", None),
        fallback_config=CONFIG,
        allow_quantized=True,
    )
    block_size = checkpoint_config.block_size

    generated_texts = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text=CONFIG.generate_start_text,
        length=CONFIG.generate_tokens,
        block_size=block_size,
        temperature=CONFIG.generate_temperature,
        top_k=CONFIG.generate_top_k,
        top_p=CONFIG.generate_top_p,
        batch_size=CONFIG.generate_batch_size,
        seed=CONFIG.generate_seed,
    )

    print("--- Generated Output ---")
    for index, text in enumerate(generated_texts, start=1):
        if len(generated_texts) > 1:
            print(f"[sample {index}]")
        print(text)
        if index < len(generated_texts):
            print()


if __name__ == "__main__":
    main()
