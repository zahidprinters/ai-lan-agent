from __future__ import annotations

"""Local reasoning facade for Phase 4.5 neural planning.

This module wraps optional llama-cpp usage behind a tiny API so the
controller can choose a local-brain backend without depending on the
underlying runtime details.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from core.inference.engine import InferenceRequest, get_default_inference_manager
from debug_utils import sentinel


@dataclass(frozen=True)
class LocalReasoningResult:
    text: str
    fallback_reason: str | None = None
    metadata: dict[str, object] | None = None


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
    task_complexity: str = "complex",
) -> LocalReasoningResult:
    """Generate local-brain response and include deterministic fallback metadata."""
    resolved_model = Path(model_path) if model_path else None
    manager = get_default_inference_manager()
    result = manager.generate(
        InferenceRequest(
            prompt=prompt,
            model_path=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            context_window=context_window,
            threads=threads,
            gpu_layers=gpu_layers,
            task_complexity=task_complexity,
        )
    )
    return LocalReasoningResult(
        text=result.text,
        fallback_reason=result.fallback_reason,
        metadata=result.metadata or None,
    )


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
    task_complexity: str = "complex",
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
        task_complexity=task_complexity,
    )
    return result.text


__all__ = [
    "LocalReasoningResult",
    "generate_structured_response",
    "generate_structured_response_result",
]
