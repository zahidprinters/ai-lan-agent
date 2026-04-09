from __future__ import annotations
from debug_utils import sentinel
import pytest
import torch
from training.dataset import CharSequenceDataset, DatasetError


@sentinel
def test_charsequencedataset_out_of_bounds() -> None:
    tokens = list(range(20))
    block_size = 5
    ds = CharSequenceDataset(tokens, block_size)
    # Valid indices: 0 to len(tokens) - block_size - 1
    valid_max = len(tokens) - block_size - 1
    # Should not raise
    _ = ds[valid_max]
    # Out of bounds: index too high
    with pytest.raises(DatasetError):
        _ = ds[len(tokens) - block_size]
    # Out of bounds: negative index
    with pytest.raises(DatasetError):
        _ = ds[-1]
