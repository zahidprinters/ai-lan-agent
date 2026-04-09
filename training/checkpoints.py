from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas

import json
import warnings
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, cast

import torch
from torch import nn

from training.config import ProjectConfig, load_config
from training.factory import build_model


def _coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


@sentinel
def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


@sentinel
def _infer_vocab_size_from_model_state(model_state: object) -> int | None:
    if not isinstance(model_state, dict):
        return None

    candidate_suffixes = (
        "token_logits.weight",
        "linear2.weight",
        "fc.weight",
        "embedding.weight",
    )
    for key, value in model_state.items():
        if not isinstance(key, str) or not key.endswith(candidate_suffixes):
            continue
        if not isinstance(value, torch.Tensor) or value.ndim < 1:
            continue
        inferred = _coerce_positive_int(value.shape[0])
        if inferred is not None:
            return inferred
    return None


@sentinel
def infer_vocab_size_from_checkpoint(checkpoint: dict[str, Any], default: int | None = None) -> int:
    tokenizer_meta = checkpoint.get("tokenizer")
    if isinstance(tokenizer_meta, dict):
        vocab_size = _coerce_positive_int(tokenizer_meta.get("vocab_size"))
        if vocab_size is not None:
            return vocab_size

    vocab_size = _coerce_positive_int(checkpoint.get("vocab_size"))
    if vocab_size is not None:
        return vocab_size

    model_vocab_size = _infer_vocab_size_from_model_state(checkpoint.get("model_state"))
    if model_vocab_size is not None:
        return model_vocab_size

    default_vocab_size = _coerce_positive_int(default)
    if default_vocab_size is not None:
        return default_vocab_size

    raise ValueError("Unable to infer vocab_size from checkpoint metadata or model state.")


@sentinel
def _quantize_model_for_inference(model: nn.Module) -> nn.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return torch.quantization.quantize_dynamic(model, {nn.Linear}, dtype=torch.qint8)


@sentinel
def load_model_from_checkpoint(
    checkpoint: dict[str, Any],
    *,
    tokenizer_vocab_size: int | None = None,
    fallback_config: ProjectConfig | None = None,
    allow_quantized: bool = True,
) -> tuple[nn.Module, ProjectConfig, int]:
    """Builds a model from checkpoint metadata and loads its weights."""
    config = load_config_from_checkpoint(checkpoint, fallback=fallback_config)
    model_type = str(checkpoint.get("model_type", config.model_type))
    vocab_size = infer_vocab_size_from_checkpoint(checkpoint, default=tokenizer_vocab_size)

    model = build_model(model_type, config=config, vocab_size=vocab_size)
    if checkpoint.get("is_quantized"):
        if not allow_quantized:
            raise ValueError(
                "Quantized checkpoints are not supported for this operation. "
                "Use a full-precision checkpoint instead."
            )
        model = _quantize_model_for_inference(model)

    model_state = checkpoint.get("model_state")
    if not isinstance(model_state, dict):
        raise ValueError("Checkpoint is missing a valid model_state mapping.")

    model.load_state_dict(model_state)
    model.eval()
    return model, config, vocab_size


@sentinel
def save_checkpoint(
    *,
    path: Path,
    model: nn.Module,
    tokenizer: Any,
    config: ProjectConfig,
    best_val_loss: float,
    model_type: str,
    optimizer: torch.optim.Optimizer | None = None,
    epoch: int | None = None,
    best_val_perplexity: float | None = None,
) -> None:
    if is_dataclass(config):
        config_payload: dict[str, Any] = asdict(config)
    elif hasattr(config, "__dict__"):
        config_payload = dict(config.__dict__)
    else:
        config_payload = {}

    # Save full config and tokenizer metadata for reproducibility
    checkpoint = {
        "version": getattr(config, "version", None),
        "model_state": model.state_dict(),
        "model_type": model_type,
        "best_val_loss": best_val_loss,
        "best_val_perplexity": best_val_perplexity,
        "epoch": epoch,
        # Store config as dict for full reproducibility
        "config": config_payload,
    }

    if optimizer is not None:
        checkpoint["optimizer_state"] = optimizer.state_dict()

    # Store tokenizer metadata if possible
    if hasattr(tokenizer, "stoi"):
        checkpoint["tokenizer"] = {
            "stoi": tokenizer.stoi,
            "unk_token": getattr(tokenizer, "UNK_TOKEN", "<UNK>"),
            "vocab_size": getattr(tokenizer, "vocab_size", len(tokenizer.stoi)),
        }

    # Ensure parent directory for weights exists
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, path)


@sentinel
def load_checkpoint(path: Path) -> dict[str, Any]:
    # This project reads checkpoints generated locally by trusted training runs.
    # Keep weights_only=False to preserve optimizer/config metadata in legacy files.
    return cast(dict[str, Any], torch.load(path, map_location="cpu", weights_only=False))


@sentinel
def load_config_from_checkpoint(
    checkpoint: dict[str, Any],
    fallback: ProjectConfig | None = None,
) -> ProjectConfig:
    """Reconstructs ProjectConfig from a checkpoint dictionary."""
    if "config" not in checkpoint:
        return fallback or load_config()

    raw_config = checkpoint["config"]
    if is_dataclass(raw_config):
        config_dict = asdict(raw_config)
    elif hasattr(raw_config, "__dict__") and not isinstance(raw_config, dict):
        config_dict = dict(raw_config.__dict__)
    else:
        config_dict = dict(raw_config)

    # Convert Path strings back to Path objects if necessary
    for key, value in config_dict.items():
        if isinstance(value, str) and (
            key.endswith("_path") or key == "runs_dir" or key == "data_path"
        ):
            config_dict[key] = Path(value)

    valid_fields = {field.name for field in fields(ProjectConfig)}
    sanitized_config = {key: value for key, value in config_dict.items() if key in valid_fields}
    return ProjectConfig(**sanitized_config)


@sentinel
def _summary_data_path(summary: dict[str, Any]) -> str:
    nested_data = summary.get("data")
    if isinstance(nested_data, dict):
        path_value = nested_data.get("path")
        if isinstance(path_value, str) and path_value:
            return path_value

    flat_data_path = summary.get("data_path")
    if isinstance(flat_data_path, str) and flat_data_path:
        return flat_data_path

    nested_paths = summary.get("paths")
    if isinstance(nested_paths, dict):
        path_value = nested_paths.get("data_path")
        if isinstance(path_value, str) and path_value:
            return path_value

    return ""


@sentinel
def normalize_run_summary(
    summary: dict[str, Any], summary_path: Path, project_data_path: Path
) -> dict[str, Any]:
    """Flattens mixed legacy/new summary schemas into a stable display shape."""
    normalized = dict(summary)
    normalized["summary_file"] = summary_path.name
    normalized["samples_file"] = summary_path.name.replace("_summary.json", "_samples.txt")

    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    hyperparameters = (
        summary.get("hyperparameters") if isinstance(summary.get("hyperparameters"), dict) else {}
    )
    data_block = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    paths_block = summary.get("paths") if isinstance(summary.get("paths"), dict) else {}

    data_path = _summary_data_path(summary)
    if data_path:
        normalized["data_path"] = data_path
        normalized["is_project_run"] = is_project_run(Path(data_path), project_data_path)
    else:
        normalized["is_project_run"] = bool(summary.get("is_project_run", False))

    aliases: list[tuple[str, dict[str, Any]]] = [
        ("best_val_loss", metrics),
        ("best_val_perplexity", metrics),
        ("final_train_loss", metrics),
        ("final_val_loss", metrics),
        ("final_train_perplexity", metrics),
        ("final_val_perplexity", metrics),
        ("train_val_gap", metrics),
        ("overfit_warning", metrics),
        ("learning_rate", hyperparameters),
        ("batch_size", hyperparameters),
        ("block_size", hyperparameters),
        ("hidden_size", hyperparameters),
        ("model_type", hyperparameters),
        ("data_size_bytes", data_block),
        ("train_token_count", data_block),
        ("val_token_count", data_block),
        ("vocab_size", data_block),
        ("model_path", paths_block),
        ("best_model_path", paths_block),
        ("tokenizer_path", paths_block),
    ]

    for key, source in aliases:
        if key not in normalized and key in source:
            normalized[key] = source[key]

    return normalized


@sentinel
def _summary_best_val_loss(summary: dict[str, Any]) -> float:
    direct_value = _coerce_float(summary.get("best_val_loss"))
    if direct_value is not None:
        return direct_value

    metrics = summary.get("metrics")
    if isinstance(metrics, dict):
        nested_value = _coerce_float(metrics.get("best_val_loss"))
        if nested_value is not None:
            return nested_value

    return float("inf")


@sentinel
def is_project_run(data_path: Path, project_data_path: Path) -> bool:
    try:
        return data_path.resolve() == project_data_path.resolve()
    except OSError:
        return False


@sentinel
def build_sorted_summaries(runs_dir: Path, project_data_path: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in runs_dir.glob("*_summary.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            normalized = normalize_run_summary(data, path, project_data_path)
            summaries.append(normalized)
        except Exception:
            continue

    summaries.sort(key=lambda item: (_summary_best_val_loss(item), item.get("timestamp", "")))
    return summaries


@sentinel
def update_run_index(config: ProjectConfig, project_data_path: Path) -> None:
    config.runs_dir.mkdir(parents=True, exist_ok=True)
    all_summaries = build_sorted_summaries(config.runs_dir, project_data_path)
    project_summaries = [item for item in all_summaries if item.get("is_project_run")]
    visible_summaries = project_summaries if project_summaries else all_summaries

    config.run_all_index_path.write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")
    config.run_index_path.write_text(json.dumps(visible_summaries, indent=2), encoding="utf-8")
    legacy_all_index_path = config.runs_dir / "all_index.json"
    if legacy_all_index_path != config.run_all_index_path:
        legacy_all_index_path.write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")


@sentinel
def save_run_artifacts(
    *,
    config: ProjectConfig,
    timestamp: str,
    tokenizer: Any,
    best_val_loss: float,
    final_train_loss: float,
    final_val_loss: float,
    sample_logs: list[str],
    train_tokens: int,
    val_tokens: int,
    model_type: str,
    project_data_path: Path,
    best_val_perplexity: float | None = None,
    final_train_perplexity: float | None = None,
    final_val_perplexity: float | None = None,
    train_val_gap: float | None = None,
    overfit_warning: str | None = None,
) -> None:
    # Ensure artifacts directory exists
    config.runs_dir.mkdir(parents=True, exist_ok=True)

    summary_path = config.runs_dir / f"{timestamp}_summary.json"
    samples_path = config.runs_dir / f"{timestamp}_samples.txt"

    vocab_size = getattr(tokenizer, "vocab_size", 0)
    if vocab_size == 0 and hasattr(tokenizer, "stoi"):
        vocab_size = len(tokenizer.stoi)

    import platform
    import sys

    summary = {
        "version": getattr(config, "version", "0.3.0"),
        "timestamp": timestamp,
        "model_type": model_type,
        "best_val_loss": best_val_loss,
        "best_val_perplexity": best_val_perplexity,
        "train_val_gap": train_val_gap,
        "overfit_warning": overfit_warning,
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version.split()[0],
            "machine": platform.machine(),
            "processor": platform.processor(),
            "device": getattr(config, "device", "cpu"),
            "use_amp": getattr(config, "use_amp", False),
        },
        "data": {
            "path": str(config.data_path),
            "size_bytes": config.data_path.stat().st_size if config.data_path.exists() else 0,
            "train_token_count": train_tokens,
            "val_token_count": val_tokens,
            "vocab_size": vocab_size,
        },
        "hyperparameters": {
            "model_type": model_type,
            "epochs": config.epochs,
            "learning_rate": config.learning_rate,
            "batch_size": config.batch_size,
            "train_ratio": config.train_ratio,
            "block_size": config.block_size,
            "hidden_size": config.hidden_size,
            "n_layer": getattr(config, "n_layer", 2),
            "n_head": getattr(config, "n_head", 1),
            "dropout": getattr(config, "dropout", 0.0),
            "stochastic_depth": getattr(config, "stochastic_depth", 0.0),
            "patience": getattr(config, "patience", 50),
        },
        "metrics": {
            "best_val_loss": best_val_loss,
            "best_val_perplexity": best_val_perplexity,
            "final_train_loss": final_train_loss,
            "final_val_loss": final_val_loss,
            "final_train_perplexity": final_train_perplexity,
            "final_val_perplexity": final_val_perplexity,
            "train_val_gap": train_val_gap,
            "overfit_warning": overfit_warning,
        },
        "paths": {
            "model_path": str(config.model_path),
            "best_model_path": str(config.best_model_path),
            "tokenizer_path": str(config.tokenizer_path),
        },
        "is_project_run": is_project_run(config.data_path, project_data_path),
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    samples_path.write_text("\n".join(sample_logs), encoding="utf-8")
    update_run_index(config, project_data_path)
