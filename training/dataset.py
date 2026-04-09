from __future__ import annotations
from debug_utils import sentinel
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset


@dataclass
class TokenSplit:
    """Dataclass holding training and validation token lists."""

    train_tokens: list[int]
    val_tokens: list[int]


class DatasetError(Exception):
    """Custom exception for errors occurring in the dataset layer."""

    pass


@sentinel
def split_tokens(tokens: list[int], block_size: int, train_ratio: float = 0.9) -> TokenSplit:
    """
    Splits a token sequence into training and validation sets.

    Args:
        tokens (list[int]): Full sequence of tokens.
        block_size (int): Context window size.
        train_ratio (float): Fraction of tokens for training.

    Returns:
        TokenSplit: Partitioned token lists.
    """
    minimum_partition_size = block_size + 1
    if len(tokens) < minimum_partition_size * 2:
        raise DatasetError(
            "Not enough tokens to build both training and validation splits. "
            "Add more text to data/input.txt or reduce BLOCK_SIZE."
        )

    split_index = int(len(tokens) * train_ratio)
    split_index = min(
        max(split_index, minimum_partition_size), len(tokens) - minimum_partition_size
    )
    return TokenSplit(
        train_tokens=tokens[:split_index],
        val_tokens=tokens[split_index:],
    )


class CharSequenceDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """
    PyTorch Dataset for causal language modeling.

    Provides (x, y) pairs where x is a context block and y is the single
    target token following that block.
    """

    @sentinel
    def __init__(
        self,
        tokens: list[int],
        block_size: int,
        batch_size: int | None = None,
        drop_last: bool = False,
    ) -> None:
        """
        Initializes the dataset with tokens and context length.

        The batch_size and drop_last parameters are kept only for API
        compatibility with older callers; batching behavior is controlled by DataLoader.
        """
        if len(tokens) <= block_size:
            raise DatasetError(
                "Not enough tokens to build a dataset for the configured block size."
            )
        self.tokens = tokens
        self.block_size = block_size
        self._batch_size_hint = batch_size
        self._drop_last_hint = drop_last

    @sentinel
    def __len__(self) -> int:
        """Returns the number of available context blocks."""
        return len(self.tokens) - self.block_size

    @sentinel
    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns a (context, target) pair for the given index.
        """
        if index < 0 or index >= len(self):
            # Print to stdout for visibility in test logs
            print(
                f"[DATASET_CRITICAL] index={index} out of range [0, {len(self)-1}]. tokens={len(self.tokens)}, block={self.block_size}"
            )
            raise DatasetError(f"Index {index} out of range [0, {len(self)-1}]")

        try:
            val_y = self.tokens[index + self.block_size]
            val_x = self.tokens[index : index + self.block_size]
            return torch.tensor(val_x, dtype=torch.long), torch.tensor(val_y, dtype=torch.long)
        except IndexError:
            print(
                f"[DATASET_CRITICAL] Internal IndexError: index={index}, tokens={len(self.tokens)}, block={self.block_size}"
            )
            raise DatasetError(f"Internal access failure at index {index}")
