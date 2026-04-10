from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from training.model_registry import promote_model, register_model


def _write_quality_artifact(
    quality_dir: Path,
    *,
    model_path: Path,
    model_version: str,
    score: float,
) -> None:
    quality_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "generated_at": "2026-04-10T00:00:00+00:00",
        "model_path": str(model_path),
        "model_version": model_version,
        "prompt_suite_path": "data/benchmarks/quality_prompts.json",
        "prompt_count": 50,
        "score": score,
        "score_source": "test",
    }
    (quality_dir / f"{model_version}_quality.json").write_text(
        json.dumps(artifact, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


def _write_settings(settings_path: Path, *, min_score: float, baseline_model: str = "") -> None:
    settings_path.write_text(
        "\n".join(
            [
                "project_name: AI Lan",
                "mode: safe",
                "default_device: cpu",
                f"quality_guardrail_min_score: {min_score}",
                f'quality_guardrail_baseline_model: "{baseline_model}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.unit
def test_quality_guardrail_allows_promotion_when_score_passes(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    settings_path = tmp_path / "settings.yaml"
    quality_dir = tmp_path / "quality"

    model_a = tmp_path / "baseline.pt"
    model_b = tmp_path / "candidate.pt"
    model_a.write_text("a", encoding="utf-8")
    model_b.write_text("b", encoding="utf-8")

    record_a = register_model(model_a, registry_path=registry_path)
    record_b = register_model(model_b, registry_path=registry_path)
    _write_settings(settings_path, min_score=0.75, baseline_model=record_a.version)
    _write_quality_artifact(quality_dir, model_path=model_a, model_version=record_a.version, score=0.80)
    _write_quality_artifact(quality_dir, model_path=model_b, model_version=record_b.version, score=0.91)

    payload = promote_model(
        record_b.version,
        registry_path=registry_path,
        settings_path=settings_path,
        quality_dir=quality_dir,
    )

    assert payload["active_version"] == record_b.version


@pytest.mark.unit
def test_quality_guardrail_blocks_promotion_below_threshold(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    settings_path = tmp_path / "settings.yaml"
    quality_dir = tmp_path / "quality"

    model_a = tmp_path / "baseline.pt"
    model_b = tmp_path / "candidate.pt"
    model_a.write_text("a", encoding="utf-8")
    model_b.write_text("b", encoding="utf-8")

    record_a = register_model(model_a, registry_path=registry_path)
    record_b = register_model(model_b, registry_path=registry_path)
    _write_settings(settings_path, min_score=0.75, baseline_model=record_a.version)
    _write_quality_artifact(quality_dir, model_path=model_a, model_version=record_a.version, score=0.80)
    _write_quality_artifact(quality_dir, model_path=model_b, model_version=record_b.version, score=0.70)

    with pytest.raises(ValueError, match="below the configured minimum"):
        promote_model(
            record_b.version,
            registry_path=registry_path,
            settings_path=settings_path,
            quality_dir=quality_dir,
        )


@pytest.mark.unit
def test_quality_guardrail_blocks_promotion_when_artifact_missing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    settings_path = tmp_path / "settings.yaml"
    quality_dir = tmp_path / "quality"

    model_a = tmp_path / "baseline.pt"
    model_b = tmp_path / "candidate.pt"
    model_a.write_text("a", encoding="utf-8")
    model_b.write_text("b", encoding="utf-8")

    record_a = register_model(model_a, registry_path=registry_path)
    record_b = register_model(model_b, registry_path=registry_path)
    _write_settings(settings_path, min_score=0.75, baseline_model=record_a.version)
    _write_quality_artifact(quality_dir, model_path=model_a, model_version=record_a.version, score=0.80)

    with pytest.raises(FileNotFoundError, match="candidate version"):
        promote_model(
            record_b.version,
            registry_path=registry_path,
            settings_path=settings_path,
            quality_dir=quality_dir,
        )


@pytest.mark.unit
def test_benchmark_quality_cli_writes_artifact(tmp_path: Path) -> None:
    model_path = tmp_path / "candidate.pt"
    output_dir = tmp_path / "quality"
    model_path.write_text("candidate", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_quality.py",
            "--model",
            str(model_path),
            "--version",
            "v-test",
            "--output-dir",
            str(output_dir),
            "--score",
            "0.87",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    payload = json.loads(result.stdout)
    artifact_path = Path(payload["output"])
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["score"] == 0.87
    assert artifact["model_version"] == "v-test"