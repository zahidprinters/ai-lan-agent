from __future__ import annotations
from debug_utils import sentinel
import torch
from torch import nn
from typing import Optional, List, Tuple


@sentinel
def _get_unknown_token(tokenizer) -> int:
    if hasattr(tokenizer, "stoi"):
        return tokenizer.stoi.get(getattr(tokenizer, "UNK_TOKEN", "<UNK>"), 0)
    return 0


@sentinel
def _apply_sampling_controls(
    *,
    logits: torch.Tensor,
    temperature: float,
    top_k: int,
    top_p: float,
    unknown_token: int,
) -> torch.Tensor:
    """
    Applies temperature, Top-K, and Top-P (Nucleus) filters to logits.
    """
    adjusted = logits.clone()
    # Mask out unknown tokens if they exist in the vocab mapping
    if unknown_token < adjusted.numel():
        adjusted[unknown_token] = float("-inf")

    adjusted = adjusted / max(temperature, 1e-5)

    # Top-k sampling
    if top_k > 0 and top_k < adjusted.numel():
        top_values, _ = torch.topk(adjusted, k=top_k)
        cutoff = top_values[-1]
        adjusted[adjusted < cutoff] = float("-inf")

    # Top-p (nucleus) sampling
    if top_p < 1.0:
        probs = torch.softmax(adjusted, dim=0)
        sorted_probs, sorted_indices = torch.sort(probs, descending=True)
        cumulative_probs = torch.cumsum(sorted_probs, dim=0)
        cutoff = (cumulative_probs > top_p).nonzero(as_tuple=True)[0]
        if len(cutoff) > 0:
            last_index = cutoff[0].item() + 1
            mask = torch.ones_like(probs, dtype=torch.bool)
            mask[sorted_indices[:last_index]] = False
            adjusted[mask] = float("-inf")

    return torch.softmax(adjusted, dim=0)


class KVGenerator:
    """
    Stateful generator that utilizes KV caching for O(1) token generation.
    Supports stop sequences for ReAct/Agentic workflows.
    """

    @sentinel
    def __init__(self, model: nn.Module, tokenizer, architecture: str = "transformer"):
        self.model = model
        self.tokenizer = tokenizer
        self.past_key_values = None
        self.cur_pos = 0
        self.architecture = architecture
        self.model.eval()

    @torch.no_grad()
    @sentinel
    def generate(
        self,
        prompt: str,
        max_length: int = 100,
        temperature: float = 1.0,
        top_k: int = 0,
        top_p: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Generates text using KV cache and optionally monitoring for stop sequences."""
        tokens = self.tokenizer.encode(prompt)
        if not tokens:
            tokens = [0]

        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        # Initial forward pass to prime the cache
        x = torch.tensor([tokens], dtype=torch.long)
        logits, self.past_key_values = self.model(x, use_cache=True)
        self.cur_pos = len(tokens)

        # Determine unknown token
        unknown_token = _get_unknown_token(self.tokenizer)

        results = tokens.copy()

        for _ in range(max_length):
            # Sample next token
            probs = _apply_sampling_controls(
                logits=logits[0, -1, :],
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                unknown_token=unknown_token,
            )
            next_token = int(torch.multinomial(probs, num_samples=1, generator=generator).item())
            results.append(next_token)

            # Check for stop sequences in the decoded text
            if stop_sequences:
                current_text = self.tokenizer.decode(results)
                if any(stop in current_text for stop in stop_sequences):
                    break

            # Incremental pass
            x_next = torch.tensor([[next_token]], dtype=torch.long)
            logits, self.past_key_values = self.model(
                x_next, start_pos=self.cur_pos, past_key_values=self.past_key_values, use_cache=True
            )
            self.cur_pos += 1

        return self.tokenizer.decode(results)


@sentinel
def sample_texts(
    *,
    model: nn.Module,
    tokenizer,
    start_text: str,
    length: int,
    block_size: int,
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: float = 1.0,
    batch_size: int = 1,
    seed: int | None = None,
    stop_sequences: Optional[List[str]] = None,
) -> list[str]:
    """
    Generates multiple independent text sequences.
    Utilizes KVGenerator for efficient caching.
    """
    results = []
    for i in range(batch_size):
        # We use a fresh generator for each batch item for now (simpler than batched KV)
        kv_gen = KVGenerator(model, tokenizer)
        # Offset seed for batch variety if provided
        item_seed = seed + i if seed is not None else None
        results.append(
            kv_gen.generate(
                prompt=start_text,
                max_length=length,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                stop_sequences=stop_sequences,
                seed=item_seed,
            )
        )
    return results


@sentinel
def sample_text(
    *,
    model: nn.Module,
    tokenizer,
    start_text: str,
    length: int,
    block_size: int,
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: float = 1.0,
    seed: int | None = None,
    stop_sequences: Optional[List[str]] = None,
) -> str:
    """
    Generates a single text sequence from a prompt with KV-Cache support.
    """
    kv_gen = KVGenerator(model, tokenizer)
    return kv_gen.generate(
        prompt=start_text,
        max_length=length,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        stop_sequences=stop_sequences,
        seed=seed,
    )


@sentinel
def streaming_text_generator(
    *,
    model: nn.Module,
    tokenizer,
    start_text: str,
    length: int,
    block_size: int,
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: float = 1.0,
    seed: int | None = None,
    yield_tokens: bool = False,
    stop_sequences: Optional[List[str]] = None,
) -> "generator":
    """
    Yields tokens or decoded text as they are generated using KV caching.
    """
    kv_gen = KVGenerator(model, tokenizer)
    tokens = tokenizer.encode(start_text)
    if not tokens:
        tokens = [0]

    generator = torch.Generator(device="cpu")
    if seed is not None:
        generator.manual_seed(seed)

    x = torch.tensor([tokens], dtype=torch.long)
    logits, pkv = model(x, use_cache=True)
    cur_pos = len(tokens)

    results = tokens.copy()
    unknown_token = _get_unknown_token(tokenizer)

    with torch.no_grad():
        for _ in range(length):
            probs = _apply_sampling_controls(
                logits=logits[0, -1, :],
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                unknown_token=unknown_token,
            )
            next_token = int(torch.multinomial(probs, num_samples=1, generator=generator).item())
            results.append(next_token)

            if stop_sequences:
                current_text = tokenizer.decode(results)
                if any(stop in current_text for stop in stop_sequences):
                    break

            if yield_tokens:
                yield next_token
            else:
                yield tokenizer.decode(results)

            # Prepare for next token
            x_next = torch.tensor([[next_token]], dtype=torch.long)
            logits, pkv = model(x_next, start_pos=cur_pos, past_key_values=pkv, use_cache=True)
            cur_pos += 1
