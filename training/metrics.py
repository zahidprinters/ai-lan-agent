from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EpochMetrics:
    train_loss: float
    val_loss: float
    best_val_loss: float
    train_perplexity: float
    val_perplexity: float
    best_val_perplexity: float
    train_val_gap: float
    overfit_warning: str


@sentinel
def loss_to_perplexity(loss: float) -> float:
    # Guard against overflow if a loss becomes unexpectedly large.
    return math.exp(min(loss, 20.0))


@sentinel
def classify_overfit_gap(gap: float) -> str:
    if gap >= 2.0:
        return "high"
    if gap >= 0.5:
        return "watch"
    return "ok"


@sentinel
def build_epoch_metrics(train_loss: float, val_loss: float, best_val_loss: float) -> EpochMetrics:
    gap = val_loss - train_loss
    return EpochMetrics(
        train_loss=train_loss,
        val_loss=val_loss,
        best_val_loss=best_val_loss,
        train_perplexity=loss_to_perplexity(train_loss),
        val_perplexity=loss_to_perplexity(val_loss),
        best_val_perplexity=loss_to_perplexity(best_val_loss),
        train_val_gap=gap,
        overfit_warning=classify_overfit_gap(gap),
    )
