from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.web_ingest import (
    IngestionSource,
    build_ingested_document,
    merge_documents,
    run_ingestion_pipeline,
    score_source_quality,
)


def test_score_source_quality_penalizes_low_quality_text() -> None:
    trusted, clean_quality = score_source_quality(
        "This is a clean technical paragraph with enough content.\nSecond line adds variety.",
        0.9,
    )
    _, noisy_quality = score_source_quality("dup\ndup\n\x01bad", 0.9)

    assert trusted == 0.9
    assert clean_quality > noisy_quality


def test_run_ingestion_pipeline_dedupes_documents_and_lines(tmp_path: Path) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("alpha\nbeta\n", encoding="utf-8")

    sources = [
        IngestionSource(
            name="local-a", source_type="file", location=str(source_file), trust_score=0.8
        ),
        IngestionSource(
            name="inline-duplicate", source_type="inline", location="alpha\nbeta", trust_score=0.7
        ),
        IngestionSource(
            name="inline-extra", source_type="inline", location="beta\ngamma", trust_score=0.7
        ),
    ]

    merged_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    report = run_ingestion_pipeline(
        sources,
        merged_output_path=merged_path,
        report_output_path=report_path,
    )

    assert report.source_count == 3
    assert report.kept_count == 2
    assert report.duplicate_count == 1
    assert merged_path.read_text(encoding="utf-8").splitlines() == ["alpha", "beta", "gamma"]

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["kept_count"] == 2
    assert len(payload["documents"]) == 2


def test_merge_documents_preserves_first_seen_order() -> None:
    documents = [
        IngestionSource(name="a", source_type="inline", location="one\ntwo", trust_score=0.6),
        IngestionSource(name="b", source_type="inline", location="two\nthree", trust_score=0.6),
    ]
    built = [build_ingested_document(source) for source in documents]

    merged = merge_documents(built)
    assert merged.splitlines() == ["one", "two", "three"]


def test_ingest_sources_cli_writes_outputs(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    merged_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "inline-a",
                    "source_type": "inline",
                    "location": "first line\nsecond line",
                    "trust_score": 0.8,
                },
                {
                    "name": "inline-b",
                    "source_type": "inline",
                    "location": "second line\nthird line",
                    "trust_score": 0.7,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_sources.py",
            "--config",
            str(config_path),
            "--output",
            str(merged_path),
            "--report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    assert "Ingestion sources: 2" in result.stdout
    assert merged_path.read_text(encoding="utf-8").splitlines() == [
        "first line",
        "second line",
        "third line",
    ]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["duplicate_count"] == 0
