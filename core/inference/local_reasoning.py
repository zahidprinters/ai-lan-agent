from __future__ import annotations

"""Local reasoning facade for Phase 4.5 neural planning.

This module wraps optional llama-cpp usage behind a tiny API so the
controller can choose a local-brain backend without depending on the
underlying runtime details.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from debug_utils import sentinel


@dataclass(frozen=True)
class LocalReasoningResult:
    text: str
    fallback_reason: str | None = None


@sentinel
def generate_structured_response_result(
    *,
    prompt: str,
    model_path: str | Path | None = None,
    max_tokens: int = 192,
    temperature: float = 0.2,
    top_p: float = 0.9,
    context_window: int = 4096,
    threads: int = 4,
    gpu_layers: int = 0,
) -> LocalReasoningResult:
    """Generate local-brain response and include deterministic fallback metadata."""
    resolved_model = Path(model_path) if model_path else None
    if resolved_model is None:
        configured = os.getenv("AI_LAN_LLAMACPP_MODEL_PATH", "").strip()
        if configured:
            resolved_model = Path(configured)

    if resolved_model is None:
        return LocalReasoningResult(text="", fallback_reason="llama_model_not_configured")
    if not resolved_model.exists():
        return LocalReasoningResult(text="", fallback_reason="llama_model_missing")

    try:
        from llama_cpp import Llama  # type: ignore[import-untyped]
    except Exception:
        return LocalReasoningResult(text="", fallback_reason="llama_runtime_unavailable")

    try:
        llm = Llama(
            model_path=str(resolved_model),
            n_ctx=context_window,
            n_threads=threads,
            n_gpu_layers=gpu_layers,
            verbose=False,
        )

        output = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=["\n\nUser:", "\n\nSYSTEM:"],
        )
        choices = output.get("choices", [])
        if not choices:
            return LocalReasoningResult(text="", fallback_reason="llama_no_choices")
        text = str(choices[0].get("text", "")).strip()
        if not text:
            return LocalReasoningResult(text="", fallback_reason="llama_empty_response")
        return LocalReasoningResult(text=text, fallback_reason=None)
    except Exception:
        return LocalReasoningResult(text="", fallback_reason="llama_runtime_error")


@sentinel
def generate_structured_response(
    *,
    prompt: str,
    model_path: str | Path | None = None,
    max_tokens: int = 192,
    temperature: float = 0.2,
    top_p: float = 0.9,
    context_window: int = 4096,
    threads: int = 4,
    gpu_layers: int = 0,
) -> str:
    """Generate a structured response with llama-cpp when available.

    Returns an empty string if llama-cpp or model path is unavailable so
    callers can deterministically fall back to the classic planner.
    """
    result = generate_structured_response_result(
        prompt=prompt,
        model_path=model_path,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        context_window=context_window,
        threads=threads,
        gpu_layers=gpu_layers,
    )
    return result.text


__all__ = [
    "LocalReasoningResult",
    "generate_structured_response",
    "generate_structured_response_result",
]
