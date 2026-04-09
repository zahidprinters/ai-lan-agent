from __future__ import annotations

"""Local text generation facade for planner and agent prompts."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from debug_utils import sentinel

from tokenizer.factory import load_tokenizer
from training.checkpoints import (
    load_checkpoint,
    load_config_from_checkpoint,
    load_model_from_checkpoint,
)
from training.config import ProjectConfig, load_config
from training.inference import sample_text


@dataclass(frozen=True)
class _GenerationBundle:
    model: Any
    tokenizer: Any
    config: ProjectConfig


def _resolve_existing_path(*candidates: object) -> Path | None:
    for candidate in candidates:
        if candidate is None:
            continue
        path = candidate if isinstance(candidate, Path) else Path(str(candidate))
        if path.exists():
            return path
    return None


@lru_cache(maxsize=1)
def _load_generation_bundle() -> _GenerationBundle | None:
    config = load_config()
    model_path = _resolve_existing_path(
        config.generate_model_path, config.best_model_path, config.model_path
    )
    tokenizer_path = _resolve_existing_path(config.generate_tokenizer_path, config.tokenizer_path)
    if model_path is None or tokenizer_path is None:
        return None

    try:
        checkpoint = load_checkpoint(model_path)
        checkpoint_config = load_config_from_checkpoint(checkpoint, fallback=config)
        resolved_tokenizer_path = _resolve_existing_path(
            getattr(checkpoint_config, "generate_tokenizer_path", None),
            getattr(checkpoint_config, "tokenizer_path", None),
            tokenizer_path,
        )
        if resolved_tokenizer_path is None:
            return None
        tokenizer = load_tokenizer(resolved_tokenizer_path)
        model, resolved_config, _ = load_model_from_checkpoint(
            checkpoint,
            tokenizer_vocab_size=getattr(tokenizer, "vocab_size", None),
            fallback_config=checkpoint_config,
            allow_quantized=True,
        )
    except Exception:
        return None

    return _GenerationBundle(model=model, tokenizer=tokenizer, config=resolved_config)


@sentinel
def generate_text(
    prompt: str,
    *,
    length: int | None = None,
    temperature: float | None = None,
    top_k: int | None = None,
    top_p: float | None = None,
    seed: int | None = None,
) -> str:
    bundle = _load_generation_bundle()
    if bundle is None:
        return ""

    if bundle.config.block_size <= 1:
        return ""

    prompt_text = prompt
    max_prompt_chars = max(bundle.config.block_size - 1, 1)
    if len(prompt_text) > max_prompt_chars:
        prompt_text = prompt_text[-max_prompt_chars:]

    generation_length = length if length is not None else bundle.config.generate_tokens
    generation_length = max(16, min(int(generation_length), 256))

    try:
        generated = sample_text(
            model=bundle.model,
            tokenizer=bundle.tokenizer,
            start_text=prompt_text,
            length=generation_length,
            block_size=bundle.config.block_size,
            temperature=(
                temperature if temperature is not None else bundle.config.generate_temperature
            ),
            top_k=top_k if top_k is not None else bundle.config.generate_top_k,
            top_p=top_p if top_p is not None else bundle.config.generate_top_p,
            seed=seed if seed is not None else bundle.config.generate_seed,
        )
    except Exception:
        return ""

    if generated.startswith(prompt_text):
        return generated[len(prompt_text) :]
    return generated


__all__ = ["generate_text"]
