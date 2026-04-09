from __future__ import annotations
from debug_utils import sentinel

# Copyright (c) 2026 Nadeem Abbas

import os
import torch
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProjectConfig:
    model_type: str = "char_mlp"
    data_path: Path = ROOT / "data" / "input.txt"
    model_path: Path = ROOT / "models" / "char_model.pt"
    best_model_path: Path = ROOT / "models" / "char_model_best.pt"
    tokenizer_path: Path = ROOT / "models" / "char_tokenizer.json"
    runs_dir: Path = ROOT / "runs"
    run_index_path: Path = ROOT / "runs" / "index.json"
    run_all_index_path: Path = ROOT / "runs" / "all_runs.json"
    block_size: int = 16
    hidden_size: int = 64
    epochs: int = 50
    learning_rate: float = 1e-3
    train_ratio: float = 0.9
    batch_size: int = 32
    sample_every: int = 10
    sample_start_text: str = ""
    sample_length: int = 50
    generate_model_path: Path = ROOT / "models" / "char_model_best.pt"
    generate_tokenizer_path: Path = ROOT / "models" / "char_tokenizer.json"
    generate_start_text: str = ""
    generate_tokens: int = 20
    generate_temperature: float = 0.8
    generate_top_k: int = 10
    generate_top_p: float = 0.9
    generate_batch_size: int = 1
    generate_seed: int | None = None
    n_layer: int = 2
    n_head: int = 1
    version: str = "0.3.0"
    lr_warmup_steps: int = 0
    lr_warmup_epochs: int = 0
    dropout: float = 0.0
    stochastic_depth: float = 0.0
    patience: int = 50
    use_amp: bool = False
    device: str = "cpu"
    debug_trace: bool = False
    debug_profile: bool = False
    sleep_mode_hour: int = 3  # 3:00 AM
    auto_promote: bool = True
    action_audit_path: str | None = None
    sleep_val_threshold: float = 1.05  # Allow 5% loss regression if logic holds
    voice_enabled: bool = False
    wake_word: str = "ai lan"
    voice_gender: str = "female"  # "male" or "female"
    voice_rate: int = 175


@sentinel
def load_config() -> ProjectConfig:
    # Define experiment profiles
    profiles = {
        "debug": {
            "epochs": 2,
            "batch_size": 4,
            "block_size": 8,
            "hidden_size": 16,
            "learning_rate": 1e-3,
            "model_type": "char_mlp",
        },
        "baseline": {
            "epochs": 50,
            "batch_size": 32,
            "block_size": 16,
            "hidden_size": 64,
            "learning_rate": 1e-3,
            "model_type": "bigram",
        },
        "transformer_small": {
            "epochs": 50,
            "batch_size": 16,
            "block_size": 16,
            "hidden_size": 32,
            "learning_rate": 1e-3,
            "model_type": "transformer",
            "n_layer": 2,
            "n_head": 1,
        },
        "transformer_medium": {
            "epochs": 50,
            "batch_size": 16,
            "block_size": 16,
            "hidden_size": 64,
            "learning_rate": 1e-3,
            "model_type": "transformer",
            "n_layer": 4,
            "n_head": 4,
        },
        "transformer_large": {
            "epochs": 50,
            "batch_size": 8,
            "block_size": 16,
            "hidden_size": 128,
            "learning_rate": 1e-3,
            "model_type": "transformer",
            "n_layer": 8,
            "n_head": 8,
        },
    }

    profile_name = os.getenv("AI_LAN_EXP_PROFILE", "").strip().lower()
    profile = profiles.get(profile_name, {})

    @sentinel
    def get_profiled_env(name, default, cast=str):
        # Priority: env var > profile > default
        env_val = os.getenv(name)
        if env_val is not None:
            return cast(env_val)
        if name.startswith("AI_LAN_"):
            key = name[7:].lower()
            if key in profile:
                return profile[key]
        return cast(default)

    data_path = Path(get_profiled_env("AI_LAN_DATA_PATH", ROOT / "data" / "input.txt"))
    runs_dir = Path(get_profiled_env("AI_LAN_RUNS_DIR", ROOT / "runs"))
    model_type = get_profiled_env("AI_LAN_MODEL_TYPE", "char_mlp").strip().lower()
    generate_seed_raw = os.getenv("AI_LAN_GENERATE_SEED")

    train_ratio = float(get_profiled_env("AI_LAN_TRAIN_RATIO", "0.9", float))
    if not (0.0 < train_ratio < 1.0):
        raise ValueError(f"AI_LAN_TRAIN_RATIO must be > 0.0 and < 1.0, got {train_ratio}.")
    version = "0.3.0"
    patience = int(get_profiled_env("AI_LAN_PATIENCE", "50", int))
    use_amp = os.getenv("AI_LAN_USE_AMP", "0").strip().lower() in ("1", "true")
    device = (
        os.getenv("AI_LAN_DEVICE", "cuda" if torch.cuda.is_available() else "cpu").strip().lower()
    )

    return ProjectConfig(
        model_type=model_type,
        use_amp=use_amp,
        device=device,
        data_path=data_path,
        model_path=Path(get_profiled_env("AI_LAN_MODEL_PATH", ROOT / "models" / "char_model.pt")),
        best_model_path=Path(
            get_profiled_env("AI_LAN_BEST_MODEL_PATH", ROOT / "models" / "char_model_best.pt")
        ),
        tokenizer_path=Path(
            get_profiled_env("AI_LAN_TOKENIZER_PATH", ROOT / "models" / "char_tokenizer.json")
        ),
        runs_dir=runs_dir,
        run_index_path=runs_dir / "index.json",
        run_all_index_path=runs_dir / "all_runs.json",
        block_size=int(get_profiled_env("AI_LAN_BLOCK_SIZE", "16", int)),
        hidden_size=int(get_profiled_env("AI_LAN_HIDDEN_SIZE", "64", int)),
        epochs=int(get_profiled_env("AI_LAN_EPOCHS", "200", int)),
        learning_rate=float(get_profiled_env("AI_LAN_LEARNING_RATE", "1e-3", float)),
        train_ratio=train_ratio,
        batch_size=int(get_profiled_env("AI_LAN_BATCH_SIZE", "32", int)),
        sample_every=int(get_profiled_env("AI_LAN_SAMPLE_EVERY", "20", int)),
        sample_start_text=get_profiled_env("AI_LAN_SAMPLE_START_TEXT", "AI "),
        sample_length=int(get_profiled_env("AI_LAN_SAMPLE_LENGTH", "120", int)),
        generate_model_path=Path(
            get_profiled_env("AI_LAN_GENERATE_MODEL_PATH", ROOT / "models" / "char_model_best.pt")
        ),
        generate_tokenizer_path=Path(
            get_profiled_env(
                "AI_LAN_GENERATE_TOKENIZER_PATH", ROOT / "models" / "char_tokenizer.json"
            )
        ),
        generate_start_text=get_profiled_env("AI_LAN_GENERATE_START_TEXT", "AI "),
        generate_tokens=int(get_profiled_env("AI_LAN_GENERATE_TOKENS", "120", int)),
        generate_temperature=float(get_profiled_env("AI_LAN_GENERATE_TEMPERATURE", "1.0", float)),
        generate_top_k=int(get_profiled_env("AI_LAN_GENERATE_TOP_K", "0", int)),
        generate_top_p=float(get_profiled_env("AI_LAN_GENERATE_TOP_P", "1.0", float)),
        generate_batch_size=int(get_profiled_env("AI_LAN_GENERATE_BATCH_SIZE", "1", int)),
        generate_seed=int(generate_seed_raw) if generate_seed_raw is not None else None,
        n_layer=int(get_profiled_env("AI_LAN_N_LAYER", "2", int)),
        n_head=int(get_profiled_env("AI_LAN_N_HEAD", "1", int)),
        version=version,
        lr_warmup_steps=int(get_profiled_env("AI_LAN_LR_WARMUP_STEPS", "0", int)),
        lr_warmup_epochs=int(get_profiled_env("AI_LAN_LR_WARMUP_EPOCHS", "0", int)),
        dropout=float(get_profiled_env("AI_LAN_DROPOUT", "0.0", float)),
        stochastic_depth=float(get_profiled_env("AI_LAN_STOCHASTIC_DEPTH", "0.0", float)),
        patience=patience,
        debug_trace=os.getenv("AI_LAN_TRACE", "0") == "1",
        debug_profile=os.getenv("AI_LAN_PROFILE", "0") == "1",
        sleep_mode_hour=int(os.getenv("AI_LAN_SLEEP_MODE_HOUR", "3")),
        auto_promote=os.getenv("AI_LAN_AUTO_PROMOTE", "1") == "1",
        action_audit_path=os.getenv("AI_LAN_ACTION_AUDIT_PATH"),
        sleep_val_threshold=float(os.getenv("AI_LAN_SLEEP_VAL_THRESHOLD", "1.05")),
        voice_enabled=os.getenv("AI_LAN_VOICE_ENABLED", "0") == "1",
        wake_word=os.getenv("AI_LAN_WAKE_WORD", "ai lan").lower(),
        voice_gender=os.getenv("AI_LAN_VOICE_GENDER", "female").lower(),
        voice_rate=int(os.getenv("AI_LAN_VOICE_RATE", "175")),
    )
