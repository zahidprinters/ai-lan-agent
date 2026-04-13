from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
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


def test_run_ingestion_pipeline_filters_low_score_sources(tmp_path: Path) -> None:
    sources = [
        IngestionSource(
            name="high-quality",
            source_type="inline",
            location=(
                "This source has rich content for trust scoring.\n"
                "Second meaningful line for quality evaluation.\n"
                "Third line keeps the document above threshold."
            ),
            trust_score=0.9,
        ),
        IngestionSource(
            name="low-quality",
            source_type="inline",
            location="dup\ndup\n\x01bad",
            trust_score=0.2,
        ),
    ]

    merged_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    report = run_ingestion_pipeline(
        sources,
        merged_output_path=merged_path,
        report_output_path=report_path,
        min_final_score=0.5,
    )

    assert report.source_count == 2
    assert report.filtered_low_score_count == 1
    assert report.kept_count == 1
    assert [document.name for document in report.documents] == ["high-quality"]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["filtered_low_score_count"] == 1


def test_run_ingestion_pipeline_applies_freshness_decay(tmp_path: Path) -> None:
    as_of = datetime(2026, 4, 13, tzinfo=UTC)
    sources = [
        IngestionSource(
            name="fresh-source",
            source_type="inline",
            location=(
                "Fresh source has useful recent content.\n"
                "Second line keeps quality high for comparison.\n"
                "Third line provides enough body for scoring."
            ),
            trust_score=0.9,
            last_updated="2026-04-12T00:00:00Z",
        ),
        IngestionSource(
            name="stale-source",
            source_type="inline",
            location=(
                "Stale source has useful old content.\n"
                "Second line keeps quality high for comparison.\n"
                "Third line provides enough body for scoring."
            ),
            trust_score=0.9,
            last_updated="2025-04-12T00:00:00Z",
        ),
    ]

    report = run_ingestion_pipeline(
        sources,
        merged_output_path=tmp_path / "merged.txt",
        report_output_path=tmp_path / "report.json",
        min_final_score=0.0,
        freshness_half_life_days=30.0,
        as_of=as_of,
    )

    assert report.kept_count == 2
    by_name = {document.name: document for document in report.documents}
    assert by_name["fresh-source"].freshness_score > by_name["stale-source"].freshness_score
    assert by_name["fresh-source"].final_score > by_name["stale-source"].final_score


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
    assert "Scheduler profile: daily" in result.stdout
    assert merged_path.read_text(encoding="utf-8").splitlines() == [
        "first line",
        "second line",
        "third line",
    ]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["duplicate_count"] == 0
    assert payload["filtered_low_score_count"] == 0


def test_ingest_sources_cli_profile_uses_settings_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    merged_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    settings_path = tmp_path / "settings.yaml"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "old-inline",
                    "source_type": "inline",
                    "location": (
                        "This document has content but is stale.\n"
                        "Second line keeps quality calculation stable.\n"
                        "Third line ensures baseline scoring remains strong."
                    ),
                    "trust_score": 0.9,
                    "last_updated": "2025-01-01T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )
    settings_path.write_text(
        "\n".join(
            [
                "ingestion_profile_default: daily",
                    "ingestion_min_final_score_deep: 0.8",
                "ingestion_freshness_half_life_days_deep: 10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_sources.py",
            "--config",
            str(config_path),
            "--settings",
            str(settings_path),
            "--profile",
            "deep",
            "--as-of",
            "2026-04-13T00:00:00Z",
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

    assert "Scheduler profile: deep" in result.stdout
    assert "Min final score: 0.8" in result.stdout
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["profile_name"] == "deep"
    assert payload["kept_count"] == 0
