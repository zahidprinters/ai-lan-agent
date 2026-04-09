from __future__ import annotations

from debug_utils import sentinel

import torch
import pytest

from tokenizer.char_tokenizer import CharTokenizer
from training.inference import sample_texts
from training.models.bigram import BigramLanguageModel


@pytest.mark.unit
@sentinel
def test_batch_generation_is_deterministic_with_seed() -> None:
    tokenizer = CharTokenizer("abc ")
    model = BigramLanguageModel(tokenizer.vocab_size)
    outputs_a = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text="a",
        length=6,
        block_size=4,
        temperature=1.0,
        top_k=0,
        batch_size=3,
        seed=42,
    )
    outputs_b = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text="a",
        length=6,
        block_size=4,
        temperature=1.0,
        top_k=0,
        batch_size=3,
        seed=42,
    )
    assert outputs_a == outputs_b
    assert len(outputs_a) == 3


@pytest.mark.unit
@sentinel
def test_top_k_generation_limits_choices() -> None:
    tokenizer = CharTokenizer("abc")
    model = BigramLanguageModel(tokenizer.vocab_size)
    with torch.no_grad():
        model.token_logits.weight.fill_(-10.0)
        model.token_logits.weight[:, tokenizer.stoi["a"]] = 5.0
        model.token_logits.weight[:, tokenizer.stoi["b"]] = 4.0
        model.token_logits.weight[:, tokenizer.stoi["c"]] = 3.0

    outputs = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text="a",
        length=8,
        block_size=4,
        temperature=1.0,
        top_k=1,
        batch_size=2,
        seed=7,
    )
    for output in outputs:
        assert set(output).issubset({"a"})


@pytest.mark.unit
@sentinel
def test_top_p_generation_limits_choices() -> None:
    tokenizer = CharTokenizer("abcd")
    model = BigramLanguageModel(tokenizer.vocab_size)
    with torch.no_grad():
        model.token_logits.weight.fill_(-10.0)
        model.token_logits.weight[:, tokenizer.stoi["a"]] = 5.0
        model.token_logits.weight[:, tokenizer.stoi["b"]] = 4.0
        model.token_logits.weight[:, tokenizer.stoi["c"]] = 3.0
        model.token_logits.weight[:, tokenizer.stoi["d"]] = 2.0

    # With top_p=0.5, only the most probable tokens should be sampled
    outputs = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text="a",
        length=8,
        block_size=4,
        temperature=1.0,
        top_k=0,
        top_p=0.5,
        batch_size=2,
        seed=7,
    )
    # Only 'a' should be present in outputs (since it has the highest prob)
    for output in outputs:
        assert set(output).issubset({"a"})

    # With top_p=0.8, 'a' and 'b' should be possible
    outputs = sample_texts(
        model=model,
        tokenizer=tokenizer,
        start_text="a",
        length=8,
        block_size=4,
        temperature=1.0,
        top_k=0,
        top_p=0.8,
        batch_size=2,
        seed=7,
    )
    for output in outputs:
        assert set(output).issubset({"a", "b"})
