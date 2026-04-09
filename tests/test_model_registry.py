from __future__ import annotations

from pathlib import Path

from training.model_registry import (
    get_active_model,
    list_registered_models,
    register_model,
    rollback_to_version,
    set_active_model,
)


def test_model_registry_register_activate_and_rollback(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    model_a = tmp_path / "a.pt"
    model_b = tmp_path / "b.pt"
    model_a.write_text("a", encoding="utf-8")
    model_b.write_text("b", encoding="utf-8")

    record_a = register_model(model_a, registry_path=registry_path, metrics={"loss": 1.2})
    record_b = register_model(model_b, registry_path=registry_path, metrics={"loss": 1.1})

    records = list_registered_models(registry_path)
    assert len(records) == 2
    set_active_model(record_b.version, registry_path)
    active_b = get_active_model(registry_path)
    assert active_b is not None
    assert active_b["version"] == record_b.version
    rollback_to_version(record_a.version, registry_path)
    active_a = get_active_model(registry_path)
    assert active_a is not None
    assert active_a["version"] == record_a.version
