from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.memory_store import add_memory_entry


def test_offline_learning_pipeline_scaffold_outputs_artifacts(tmp_path: Path) -> None:
    memory_db = tmp_path / "memory.sqlite3"
    merged_corpus = tmp_path / "merged.txt"
    dataset_output = tmp_path / "learning_dataset.txt"
    registry_path = tmp_path / "registry.json"

    add_memory_entry(
        kind="notes",
        content="Policy rules require confirmation for write-like actions.",
        db_path=memory_db,
    )
    merged_corpus.write_text("trusted corpus line one\ntrusted corpus line two\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/offline_learning_pipeline.py",
            "--memory-db",
            str(memory_db),
            "--merged-corpus",
            str(merged_corpus),
            "--dataset-output",
            str(dataset_output),
            "--registry",
            str(registry_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    payload = json.loads(result.stdout)
    assert dataset_output.exists()
    assert Path(payload["candidate_meta"]).exists()
    assert "canary" in payload
    assert payload["registry_record"] is None
    assert payload["promotion_skipped_reason"] is None
    assert not Path(payload["candidate_meta"]).with_name("candidate_model.placeholder").exists()
