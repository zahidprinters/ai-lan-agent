from __future__ import annotations
from debug_utils import sentinel

import pytest

from training.config import load_config

PROFILE_OVERRIDE_KEYS = [
    "AI_LAN_EPOCHS",
    "AI_LAN_BATCH_SIZE",
    "AI_LAN_BLOCK_SIZE",
    "AI_LAN_HIDDEN_SIZE",
    "AI_LAN_MODEL_TYPE",
]


def _clear_profile_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in PROFILE_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.unit
@sentinel
def test_config_rejects_invalid_train_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_TRAIN_RATIO", "1.0")
    with pytest.raises(ValueError, match="AI_LAN_TRAIN_RATIO"):
        load_config()


@pytest.mark.unit
@sentinel
def test_config_reads_bigram_model_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_MODEL_TYPE", "bigram")
    config = load_config()
    assert config.model_type == "bigram"


@pytest.mark.unit
@sentinel
def test_config_reads_generation_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_GENERATE_TEMPERATURE", "0.8")
    monkeypatch.setenv("AI_LAN_GENERATE_TOP_K", "5")
    monkeypatch.setenv("AI_LAN_GENERATE_BATCH_SIZE", "3")
    monkeypatch.setenv("AI_LAN_GENERATE_SEED", "123")
    config = load_config()
    assert config.generate_temperature == 0.8
    assert config.generate_top_k == 5
    assert config.generate_batch_size == 3
    assert config.generate_seed == 123


@pytest.mark.unit
@sentinel
def test_config_profile_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_profile_override_env(monkeypatch)
    monkeypatch.setenv("AI_LAN_EXP_PROFILE", "debug")
    config = load_config()
    assert config.epochs == 2
    assert config.batch_size == 4
    assert config.block_size == 8
    assert config.hidden_size == 16
    assert config.model_type == "char_mlp"


@pytest.mark.unit
@sentinel
def test_config_profile_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_profile_override_env(monkeypatch)
    monkeypatch.setenv("AI_LAN_EXP_PROFILE", "baseline")
    config = load_config()
    assert config.epochs == 50
    assert config.batch_size == 32
    assert config.block_size == 16
    assert config.hidden_size == 64
    assert config.model_type == "bigram"


@pytest.mark.unit
@sentinel
def test_config_profile_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_profile_override_env(monkeypatch)
    monkeypatch.setenv("AI_LAN_EXP_PROFILE", "debug")
    monkeypatch.setenv("AI_LAN_EPOCHS", "99")
    config = load_config()
    assert config.epochs == 99


@pytest.mark.unit
@sentinel
def test_config_exposes_debug_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_DEBUG", "1")
    monkeypatch.setenv("AI_LAN_TRACE", "1")
    monkeypatch.setenv("AI_LAN_PROFILE", "0")
    monkeypatch.setenv("AI_LAN_TRACE_STDOUT", "1")

    config = load_config()

    assert config.debug.debug_enabled is True
    assert config.debug.trace_enabled is True
    assert config.debug.profile_enabled is False
    assert config.debug.trace_stdout_enabled is True
    # Backward compatibility fields still mirror centralized settings.
    assert config.debug_trace is True
    assert config.debug_profile is False


@pytest.mark.unit
@sentinel
def test_config_reads_perception_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_PERCEPTION_ENABLED", "1")
    monkeypatch.setenv("AI_LAN_PERCEPTION_INTERVAL_SEC", "7")

    config = load_config()

    assert config.perception_enabled is True
    assert config.perception_interval_sec == 7


@pytest.mark.unit
@sentinel
def test_config_reads_runtime_optimization_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_PERCEPTION_MAX_INTERVAL_SEC", "45")
    monkeypatch.setenv("AI_LAN_PERCEPTION_ADAPTIVE", "0")
    monkeypatch.setenv("AI_LAN_RUNTIME_CONTEXT_MAX_CHARS", "2048")

    config = load_config()

    assert config.perception_max_interval_sec == 45
    assert config.perception_adaptive is False
    assert config.runtime_context_max_chars == 2048
