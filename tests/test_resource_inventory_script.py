from __future__ import annotations

from pathlib import Path

from scripts import regenerate_resource_inventory as audit


def test_build_package_snapshot_text_contains_python_header() -> None:
    text = audit.build_package_snapshot_text(Path("D:/repo/.venv/Scripts/python.exe"), "3.11.9")

    assert "AI Lan local Python package snapshot" in text
    assert "Python: 3.11.9" in text
    assert "Executable: D:/repo/.venv/Scripts/python.exe" in text


def test_build_inventory_markdown_includes_key_sections(tmp_path: Path) -> None:
    root = tmp_path
    (root / "temp" / "downloads" / "phase4").mkdir(parents=True)
    (root / "temp" / "downloads" / "phase45").mkdir(parents=True)
    (root / "temp" / "downloads" / "phase5").mkdir(parents=True)
    (root / "models" / "downloads").mkdir(parents=True)
    (root / "models" / "vosk-model-small-en-us-0.15").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    (root / "runs").mkdir(parents=True)
    (root / ".venv").mkdir(parents=True)
    (root / "models" / "downloads" / "vosk-model-small-en-us-0.15.zip").write_bytes(b"zip")
    (root / "models" / "downloads" / "tinyllama-1.1b-chat-v1.0.Q2_K.gguf").write_bytes(b"gguf")
    (root / "data" / "tinystories.txt").write_text("story", encoding="utf-8")

    markdown = audit.build_inventory_markdown(root, Path("D:/repo/.venv/Scripts/python.exe"), "3.11.9")

    assert "# AI Lan Resource Inventory" in markdown
    assert "## Project Virtual Environment" in markdown
    assert "## Temporary Working Area" in markdown
    assert "## Models And Downloaded Assets" in markdown
    assert "## One-Command Audit Workflow" in markdown