"""Tesseract OCR adapter for Phase 4 perception layer.

Uses ``pytesseract`` (Python binding) backed by the system Tesseract binary.
Automatically locates the Windows default install path when the binary is
not on PATH so the rest of the stack never hard-codes paths.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from debug_utils import sentinel

# Common Windows install paths tried in order when Tesseract is not on PATH.
_WIN_TESSERACT_DEFAULTS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _configure_tesseract() -> None:
    """Point pytesseract at the Tesseract binary if not already on PATH."""
    try:
        import pytesseract  # type: ignore[import-untyped]
        import shutil

        if shutil.which("tesseract"):
            return  # already discoverable

        for candidate in _WIN_TESSERACT_DEFAULTS:
            if Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                return
    except ImportError:
        pass


def _coerce_confidence(raw_value: object) -> float | None:
    try:
        value = float(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def _extract_tesseract_confidence(
    image_path: str,
    *,
    min_confidence: float,
) -> dict[str, object]:
    import pytesseract  # type: ignore[import-untyped]
    from PIL import Image

    with Image.open(image_path) as img:
        raw_text = str(pytesseract.image_to_string(img)).strip()

        try:
            data = pytesseract.image_to_data(  # type: ignore[attr-defined]
                img,
                output_type=pytesseract.Output.DICT,
            )
            words = data.get("text", [])
            confidences = data.get("conf", [])
        except Exception:
            words = []
            confidences = []

    kept_tokens: list[str] = []
    kept_confidences: list[float] = []
    considered_count = 0
    for word, confidence_raw in zip(words, confidences):
        token = str(word).strip()
        if not token:
            continue
        confidence = _coerce_confidence(confidence_raw)
        if confidence is None:
            continue
        considered_count += 1
        if confidence >= float(min_confidence):
            kept_tokens.append(token)
            kept_confidences.append(confidence)

    filtered_text = " ".join(kept_tokens).strip()
    average_confidence = (
        round(sum(kept_confidences) / len(kept_confidences), 3)
        if kept_confidences
        else None
    )
    return {
        "status": "ok",
        "text": raw_text,
        "filtered_text": filtered_text,
        "average_confidence": average_confidence,
        "tokens_considered": considered_count,
        "tokens_kept": len(kept_tokens),
        "detail": "",
        "backend": "tesseract",
    }


def _extract_easyocr_confidence(
    image_path: str,
    *,
    min_confidence: float,
) -> dict[str, object]:
    reader = _get_easyocr_reader()
    results = reader.readtext(image_path)
    all_tokens: list[str] = []
    kept_tokens: list[str] = []
    kept_confidences: list[float] = []

    for item in results:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        token = str(item[1]).strip()
        confidence_raw = item[2]
        if not token:
            continue
        all_tokens.append(token)
        confidence = _coerce_confidence(float(confidence_raw) * 100.0)
        if confidence is None:
            continue
        if confidence >= float(min_confidence):
            kept_tokens.append(token)
            kept_confidences.append(confidence)

    raw_text = " ".join(all_tokens).strip()
    filtered_text = " ".join(kept_tokens).strip()
    average_confidence = (
        round(sum(kept_confidences) / len(kept_confidences), 3)
        if kept_confidences
        else None
    )
    return {
        "status": "ok",
        "text": raw_text,
        "filtered_text": filtered_text,
        "average_confidence": average_confidence,
        "tokens_considered": len(all_tokens),
        "tokens_kept": len(kept_tokens),
        "detail": "",
        "backend": "easyocr",
    }


@lru_cache(maxsize=1)
def _get_easyocr_reader() -> Any:
    import easyocr  # type: ignore[import-untyped]

    return easyocr.Reader(["en"], gpu=False)


def _has_usable_ocr_text(result: dict[str, object]) -> bool:
    filtered_text = str(result.get("filtered_text", "")).strip()
    raw_text = str(result.get("text", "")).strip()
    tokens_kept = int(result.get("tokens_kept", 0) or 0)
    return bool(filtered_text or raw_text or tokens_kept > 0)


@sentinel
def run_ocr_with_confidence(
    image_path: str,
    *,
    min_confidence: float = 45.0,
    backend: str = "auto",
    enable_easyocr_fallback: bool = True,
) -> dict[str, object]:
    """Run OCR and keep only tokens above the configured confidence threshold.

    Returns keys: ``status``, ``text``, ``filtered_text``, ``average_confidence``,
    ``tokens_considered``, ``tokens_kept``, and ``detail``.
    """
    _configure_tesseract()
    resolved_backend = backend.strip().lower()
    if resolved_backend not in {"auto", "tesseract", "easyocr"}:
        return {
            "status": "failed",
            "text": "",
            "filtered_text": "",
            "average_confidence": None,
            "tokens_considered": 0,
            "tokens_kept": 0,
            "detail": f"Unsupported OCR backend: {backend}",
            "backend": "none",
        }

    last_error = ""
    try:
        if resolved_backend in {"auto", "tesseract"}:
            tesseract_result = _extract_tesseract_confidence(
                image_path,
                min_confidence=min_confidence,
            )
            if resolved_backend == "tesseract" or _has_usable_ocr_text(tesseract_result):
                return tesseract_result
            last_error = "tesseract returned no usable OCR text"
    except ImportError as exc:
        last_error = f"tesseract unavailable: {exc}"
        if not enable_easyocr_fallback or resolved_backend == "tesseract":
            return {
                "status": "failed",
                "text": "",
                "filtered_text": "",
                "average_confidence": None,
                "tokens_considered": 0,
                "tokens_kept": 0,
                "detail": last_error,
                "backend": "tesseract",
            }
    except Exception as exc:
        last_error = str(exc)
        if not enable_easyocr_fallback or resolved_backend == "tesseract":
            return {
                "status": "failed",
                "text": "",
                "filtered_text": "",
                "average_confidence": None,
                "tokens_considered": 0,
                "tokens_kept": 0,
                "detail": last_error,
                "backend": "tesseract",
            }

    try:
        if resolved_backend in {"auto", "easyocr"}:
            return _extract_easyocr_confidence(
                image_path,
                min_confidence=min_confidence,
            )
    except ImportError as exc:
        if last_error:
            detail = f"{last_error}; easyocr unavailable: {exc}"
        else:
            detail = f"easyocr unavailable: {exc}"
        return {
            "status": "failed",
            "text": "",
            "filtered_text": "",
            "average_confidence": None,
            "tokens_considered": 0,
            "tokens_kept": 0,
            "detail": detail,
            "backend": "easyocr",
        }
    except FileNotFoundError as exc:
        return {
            "status": "failed",
            "text": "",
            "filtered_text": "",
            "average_confidence": None,
            "tokens_considered": 0,
            "tokens_kept": 0,
            "detail": f"Image not found: {exc}",
            "backend": "none",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "text": "",
            "filtered_text": "",
            "average_confidence": None,
            "tokens_considered": 0,
            "tokens_kept": 0,
            "detail": str(exc),
            "backend": "none",
        }

    return {
        "status": "failed",
        "text": "",
        "filtered_text": "",
        "average_confidence": None,
        "tokens_considered": 0,
        "tokens_kept": 0,
        "detail": "No OCR backend was selected.",
        "backend": "none",
    }


@sentinel
def run_ocr(image_path: str) -> dict[str, str]:
    """Run Tesseract OCR on the given image file.

    Returns a dict with keys ``status``, ``text``, ``detail``.
    """
    detailed = run_ocr_with_confidence(image_path=image_path)
    status = str(detailed.get("status", "failed"))
    detail = str(detailed.get("detail", ""))
    filtered_text = str(detailed.get("filtered_text", "")).strip()
    raw_text = str(detailed.get("text", "")).strip()
    return {
        "status": status,
        "text": filtered_text or raw_text,
        "detail": detail,
    }


@sentinel
def run_ocr_from_screenshot() -> dict[str, str]:
    """Capture the current screen and run OCR on it.

    Writes the screenshot to ``temp/ocr/screen.png`` and runs OCR.
    Returns the same dict shape as ``run_ocr``.
    """
    _configure_tesseract()
    from pathlib import Path as P

    try:
        import mss  # type: ignore[import-untyped]
        from PIL import Image as PILImage

        dest = P("temp") / "ocr" / "screen.png"
        dest.parent.mkdir(parents=True, exist_ok=True)

        with mss.mss() as sct:
            sct.shot(output=str(dest))

        return run_ocr(str(dest))
    except ImportError as exc:
        return {"status": "failed", "text": "", "detail": f"mss not installed: {exc}"}
    except Exception as exc:
        return {"status": "failed", "text": "", "detail": str(exc)}


__all__ = ["run_ocr", "run_ocr_from_screenshot", "run_ocr_with_confidence"]
