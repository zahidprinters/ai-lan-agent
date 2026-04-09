from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal, cast

from debug_utils import sentinel

from training.corpus import analyze_text

SourceType = Literal["file", "http", "inline"]
VALID_SOURCE_TYPES: set[SourceType] = {"file", "http", "inline"}


@dataclass(frozen=True)
class IngestionSource:
    name: str
    source_type: SourceType
    location: str
    trust_score: float = 0.5


@dataclass(frozen=True)
class IngestedDocument:
    name: str
    source_type: SourceType
    location: str
    normalized_text: str
    trust_score: float
    quality_score: float
    final_score: float
    line_count: int
    char_count: int
    content_hash: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IngestionReport:
    source_count: int
    fetched_count: int
    kept_count: int
    duplicate_count: int
    merged_line_count: int
    merged_char_count: int
    documents: list[IngestedDocument]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["documents"] = [document.to_dict() for document in self.documents]
        return payload


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


@sentinel
def load_ingestion_sources(config_path: Path) -> list[IngestionSource]:
    raw_sources = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw_sources, list):
        raise ValueError("Ingestion config must be a JSON array.")

    sources: list[IngestionSource] = []
    for item in raw_sources:
        if not isinstance(item, dict):
            raise ValueError("Each ingestion source entry must be an object.")
        source_type_raw = str(item["source_type"])
        if source_type_raw not in VALID_SOURCE_TYPES:
            raise ValueError(f"Unsupported source_type '{source_type_raw}' in ingestion config.")
        sources.append(
            IngestionSource(
                name=str(item["name"]),
                source_type=cast(SourceType, source_type_raw),
                location=str(item["location"]),
                trust_score=float(item.get("trust_score", 0.5)),
            )
        )
    return sources


@sentinel
def fetch_source_text(source: IngestionSource) -> str:
    if source.source_type == "inline":
        return source.location
    if source.source_type == "file":
        return Path(source.location).read_text(encoding="utf-8")
    if source.source_type == "http":
        import requests  # type: ignore[import-untyped]

        response = requests.get(source.location, timeout=20)
        response.raise_for_status()
        return cast(str, response.text)
    raise ValueError(f"Unsupported source type: {source.source_type}")


@sentinel
def fetch_source_content(source: IngestionSource) -> str:
    """Backward-compatible alias for fetch_source_text."""
    return fetch_source_text(source)


@sentinel
def normalize_ingested_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.strip() for line in normalized.split("\n")]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines).strip()


@sentinel
def normalize_text(text: str) -> str:
    """Backward-compatible alias for normalize_ingested_text."""
    return normalize_ingested_text(text)


@sentinel
def score_source_quality(text: str, trust_score: float) -> tuple[float, float]:
    report = analyze_text(text, path=Path("<ingested>"))
    if report.non_empty_line_count == 0 or report.total_characters == 0:
        return _clamp_score(trust_score), 0.0

    quality = 1.0
    duplicate_ratio = report.duplicate_line_count / max(report.non_empty_line_count, 1)
    suspicious_ratio = sum(count for _, count in report.suspicious_characters) / max(
        report.total_characters, 1
    )
    average_line_length = report.total_characters / max(report.non_empty_line_count, 1)

    if duplicate_ratio > 0.25:
        quality -= 0.25
    elif duplicate_ratio > 0.1:
        quality -= 0.1

    if suspicious_ratio > 0.05:
        quality -= 0.3
    elif suspicious_ratio > 0.01:
        quality -= 0.1

    if average_line_length < 20:
        quality -= 0.1

    if report.non_empty_line_count < 3:
        quality -= 0.1

    bounded_trust = _clamp_score(trust_score)
    return bounded_trust, _clamp_score(quality)


@sentinel
def build_ingested_document(source: IngestionSource) -> IngestedDocument:
    raw_text = fetch_source_text(source)
    normalized_text = normalize_ingested_text(raw_text)
    trust_score, quality_score = score_source_quality(normalized_text, source.trust_score)
    final_score = _clamp_score((trust_score + quality_score) / 2.0)
    line_count = len(normalized_text.splitlines()) if normalized_text else 0
    char_count = len(normalized_text)
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return IngestedDocument(
        name=source.name,
        source_type=source.source_type,
        location=source.location,
        normalized_text=normalized_text,
        trust_score=trust_score,
        quality_score=quality_score,
        final_score=final_score,
        line_count=line_count,
        char_count=char_count,
        content_hash=content_hash,
    )


@sentinel
def dedupe_documents(documents: Iterable[IngestedDocument]) -> tuple[list[IngestedDocument], int]:
    kept: list[IngestedDocument] = []
    seen_hashes: set[str] = set()
    duplicate_count = 0
    for document in documents:
        if not document.normalized_text:
            duplicate_count += 1
            continue
        if document.content_hash in seen_hashes:
            duplicate_count += 1
            continue
        seen_hashes.add(document.content_hash)
        kept.append(document)
    return kept, duplicate_count


@sentinel
def merge_documents(documents: Iterable[IngestedDocument]) -> str:
    seen_lines: set[str] = set()
    merged_lines: list[str] = []
    for document in documents:
        for line in document.normalized_text.splitlines():
            if line in seen_lines:
                continue
            seen_lines.add(line)
            merged_lines.append(line)
    return "\n".join(merged_lines) + ("\n" if merged_lines else "")


@sentinel
def run_ingestion_pipeline(
    sources: list[IngestionSource],
    *,
    merged_output_path: Path,
    report_output_path: Path,
) -> IngestionReport:
    merged_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)

    documents = [build_ingested_document(source) for source in sources]
    deduped_documents, duplicate_count = dedupe_documents(documents)
    merged_text = merge_documents(deduped_documents)

    merged_output_path.write_text(merged_text, encoding="utf-8")

    report = IngestionReport(
        source_count=len(sources),
        fetched_count=len(documents),
        kept_count=len(deduped_documents),
        duplicate_count=duplicate_count,
        merged_line_count=len(merged_text.splitlines()),
        merged_char_count=len(merged_text),
        documents=deduped_documents,
    )
    report_output_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return report
