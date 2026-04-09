from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas
"""
StackedTransformer: Multi-layer transformer model with KV Caching and RoPE.
Includes professional-grade Rotary Positional Embeddings (RoPE) and 
efficient inference acceleration via past_key_values support.
"""

import torch
from torch import nn
import torch.nn.functional as F
from typing import Optional, Tuple, List


@sentinel
def precompute_rope_freqs(dim: int, seq_len: int, theta: float = 10000.0) -> torch.Tensor:
    """Precomputes real-valued cosine and sine tables for RoPE."""
    inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float32)[: (dim // 2)] / dim))
    t = torch.arange(seq_len, dtype=torch.float32, device=inv_freq.device)
    freqs = torch.outer(t, inv_freq)
    return torch.stack((freqs.cos(), freqs.sin()), dim=-1)


@sentinel
def apply_rope(x: torch.Tensor, rope_cache: torch.Tensor) -> torch.Tensor:
    """Applies Rotary Positional Embeddings to the input tensor."""
    if x.shape[-1] % 2 != 0:
        raise ValueError("RoPE requires an even head dimension.")

    rope_cache = rope_cache.to(dtype=x.dtype, device=x.device)
    cos = rope_cache[..., 0].unsqueeze(0).unsqueeze(2)
    sin = rope_cache[..., 1].unsqueeze(0).unsqueeze(2)

    x_even = x[..., ::2]
    x_odd = x[..., 1::2]
    x_rotated = torch.stack((x_even * cos - x_odd * sin, x_even * sin + x_odd * cos), dim=-1)
    return x_rotated.flatten(-2)


class CausalSelfAttention(nn.Module):
    """
    Custom Self-Attention implementation with RoPE and KV Caching.
    Supports efficient incremental generation (O(1) per token).
    """

    @sentinel
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.0) -> None:
        super().__init__()
        assert hidden_size % num_heads == 0, "Hidden size must be divisible by num_heads."

        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False)

        self.dropout = nn.Dropout(dropout)

    @sentinel
    def forward(
        self,
        x: torch.Tensor,
        rope_cache: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        batch, seq_len, _ = x.shape

        q = self.q_proj(x).view(batch, seq_len, self.num_heads, self.head_dim)
        k = self.k_proj(x).view(batch, seq_len, self.num_heads, self.head_dim)
        v = self.v_proj(x).view(batch, seq_len, self.num_heads, self.head_dim)

        # Apply RoPE
        # For incremental generation, we need to apply RoPE based on the current position
        # past_key_value sequence length + current seq_len
        q = apply_rope(q, rope_cache)
        k = apply_rope(k, rope_cache)

        if past_key_value is not None:
            prev_k, prev_v = past_key_value
            k = torch.cat([prev_k, k], dim=1)
            v = torch.cat([prev_v, v], dim=1)

        kv_cache = (k, v) if use_cache else None

        # Efficient Attention (Scaled Dot-Product)
        # (batch, num_heads, seq_len, head_dim)
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        attn_mask = mask
        if attn_mask is not None:
            attn_mask = attn_mask.unsqueeze(0).unsqueeze(0)

        out = (
            F.scaled_dot_product_attention(
                q,
                k,
                v,
                attn_mask=attn_mask,
                dropout_p=self.dropout.p if self.training else 0.0,
            )
            .transpose(1, 2)
            .reshape(batch, seq_len, self.hidden_size)
        )
        return self.o_proj(out), kv_cache


class Block(nn.Module):
    """
    Enhanced Transformer Block with LayerNorm and CausalSelfAttention.
    Supports Stochastic Depth (DropPath).
    """

    @sentinel
    def __init__(
        self,
        hidden_size: int,
        num_heads: int = 1,
        dropout: float = 0.0,
        stochastic_depth: float = 0.0,
    ) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(hidden_size)
        self.attn = CausalSelfAttention(hidden_size, num_heads, dropout)
        self.ln2 = nn.LayerNorm(hidden_size)
        self.ff = nn.Sequential(
            nn.Linear(hidden_size, 4 * hidden_size, bias=False),
            nn.GELU(),
            nn.Linear(4 * hidden_size, hidden_size, bias=False),
        )
        self.dropout = nn.Dropout(dropout)
        self.stochastic_depth = stochastic_depth

    @sentinel
    def forward(
        self,
        x: torch.Tensor,
        rope_cache: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        past_key_value: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        # Attention with Residual + Stochastic Depth
        h, new_kv = self.attn(self.ln1(x), rope_cache, mask, past_key_value, use_cache)

        if self.training and self.stochastic_depth > 0:
            if torch.rand(1).item() > self.stochastic_depth:
                x = x + h
        else:
            x = x + h

        # FFN with Residual + Stochastic Depth
        h_ff = self.ff(self.ln2(x))
        if self.training and self.stochastic_depth > 0:
            if torch.rand(1).item() > self.stochastic_depth:
                x = x + h_ff
        else:
            x = x + h_ff

        return x, new_kv


class StackedTransformer(nn.Module):
    """
    Professional Transformer with KV Caching, RoPE, and Staged Processing.
    """

    @sentinel
    def __init__(
        self,
        vocab_size: int,
        block_size: int,
        hidden_size: int,
        num_layers: int = 2,
        num_heads: int = 1,
        dropout: float = 0.0,
        stochastic_depth: float = 0.0,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.block_size = block_size
        self.hidden_size = hidden_size
        assert (hidden_size // num_heads) % 2 == 0, "RoPE head dimension must be even."

        self.embedding = nn.Embedding(vocab_size, hidden_size)

        # Linear decay for stochastic depth across layers
        d_rates = [x.item() for x in torch.linspace(0, stochastic_depth, num_layers)]

        self.layers = nn.ModuleList(
            [Block(hidden_size, num_heads, dropout, d_rates[i]) for i in range(num_layers)]
        )
        self.norm = nn.LayerNorm(hidden_size)
        self.fc = nn.Linear(hidden_size, vocab_size, bias=False)

        # Precompute RoPE freqs
        self.register_buffer(
            "rope_cache", precompute_rope_freqs(hidden_size // num_heads, block_size)
        )

        # Causal Mask
        mask = torch.full((block_size, block_size), float("-inf"))
        mask = torch.triu(mask, diagonal=1)
        self.register_buffer("causal_mask", mask)

    @sentinel
    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        past_key_values: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False,
    ) -> torch.Tensor | Tuple[torch.Tensor, Optional[List[Tuple[torch.Tensor, torch.Tensor]]]]:
        batch, seq_len = x.shape
        h = self.embedding(x)

        # Slice precomputed RoPE frequencies
        rope_cache = self.rope_cache[start_pos : start_pos + seq_len]

        # Slice and Adjust Mask
        # If we have past KVs, the current tokens attend to themselves and ALL previous tokens
        mask = None
        if seq_len > 1:
            mask = self.causal_mask[:seq_len, :seq_len]
            # When using KV cache and seq_len=1, we don't need a mask as we only attend to the past

        new_kvs = [] if use_cache else None

        for i, layer in enumerate(self.layers):
            pkv = past_key_values[i] if past_key_values is not None else None
            h, kv = layer(h, rope_cache, mask, pkv, use_cache)
            if use_cache:
                new_kvs.append(kv)

        h = self.norm(h)
        logits = self.fc(h)

        if use_cache:
            return logits, new_kvs
        else:
            return logits

    @sentinel
    def inference(self, x: torch.Tensor) -> torch.Tensor:
        """Standard full-window inference."""
        output = self.forward(x)
        logits = output[0] if isinstance(output, tuple) else output
        return logits[:, -1, :]
