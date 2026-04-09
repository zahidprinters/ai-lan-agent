from __future__ import annotations

import json
from pathlib import Path

from api.server import build_dashboard_state, create_app
from runtime.chat_interface import ChatSession
from tools.memory_store import add_memory_entry
from training.config import load_config


def test_dashboard_state_includes_runs_models_memory_and_logs(tmp_path: Path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    data_path = tmp_path / "input.txt"
    data_path.write_text("docs are safe to list\n", encoding="utf-8")

    summary_path = runs_dir / "20260405_000000_summary.json"
    summary_payload = {
        "timestamp": "20260405_000000",
        "model_type": "char_mlp",
        "metrics": {
            "best_val_loss": 1.0,
            "best_val_perplexity": 2.0,
            "final_train_loss": 1.1,
            "final_val_loss": 1.0,
        },
        "hyperparameters": {
            "model_type": "char_mlp",
            "learning_rate": 0.001,
            "batch_size": 4,
            "block_size": 16,
            "hidden_size": 32,
        },
        "data": {
            "path": str(data_path),
            "train_token_count": 100,
            "val_token_count": 10,
            "vocab_size": 50,
        },
        "paths": {
            "model_path": str(tmp_path / "models" / "model.pt"),
            "best_model_path": str(tmp_path / "models" / "best.pt"),
            "tokenizer_path": str(tmp_path / "models" / "tokenizer.json"),
        },
    }
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    registry_path = runs_dir / "model_registry.json"
    registry_payload = {
        "active_version": "v1",
        "records": [
            {
                "version": "v1",
                "model_path": str(tmp_path / "models" / "model.pt"),
                "created_at": "2026-04-05T00:00:00+00:00",
                "metrics": {"accuracy": 0.9},
                "tags": ["demo"],
                "notes": "test record",
            }
        ],
    }
    registry_path.write_text(
        json.dumps(registry_payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )

    audit_path = tmp_path / "audit.jsonl"
    audit_payload = {
        "timestamp": "2026-04-05T00:00:00+00:00",
        "request": {
            "thought": "List docs",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 3},
            "safety_level": "low",
        },
        "result": {
            "status": "executed",
            "action": "pc.list_workspace_files",
            "observation": {"status": "ok"},
            "policy_reason": "allowed",
        },
    }
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=True) + "\n", encoding="utf-8")

    merged_path = tmp_path / "merged.txt"
    merged_path.write_text("docs are safe to list\n", encoding="utf-8")
    memory_db = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Docs are safe to list inside the workspace.",
        metadata={"topic": "docs"},
        db_path=memory_db,
    )

    monkeypatch.setenv("AI_LAN_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("AI_LAN_DATA_PATH", str(data_path))
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(audit_path))

    session = ChatSession(memory_db_path=memory_db, merged_corpus_path=merged_path)
    session.handle_message("hello")

    config = load_config()
    app = create_app(session=session, config=config)
    state = build_dashboard_state(app, query="docs")

    assert state["runs"]["project_run_count"] == 1
    assert state["runs"]["visible_run_count"] == 1
    assert state["models"]["record_count"] == 1
    assert state["models"]["active"]["active_version"] == "v1"
    assert state["logs"]["audit_entries"]
    assert state["memory"]["query"] == "docs"
    assert state["context"]["query"] == "docs"
    assert state["ops"]["paths"]["memory_db_path"] == str(memory_db)
