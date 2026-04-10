"""Tesseract OCR adapter for Phase 4 perception layer.

Uses ``pytesseract`` (Python binding) backed by the system Tesseract binary.
Automatically locates the Windows default install path when the binary is
not on PATH so the rest of the stack never hard-codes paths.
"""

from __future__ import annotations

import os
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


@sentinel
def run_ocr(image_path: str) -> dict[str, str]:
    """Run Tesseract OCR on the given image file.

    Returns a dict with keys ``status``, ``text``, ``detail``.
    """
    _configure_tesseract()
    try:
        import pytesseract  # type: ignore[import-untyped]
        from PIL import Image

        img = Image.open(image_path)
        text: str = pytesseract.image_to_string(img)
        return {"status": "ok", "text": text.strip(), "detail": ""}
    except ImportError as exc:
        return {"status": "failed", "text": "", "detail": f"pytesseract not installed: {exc}"}
    except FileNotFoundError as exc:
        return {"status": "failed", "text": "", "detail": f"Image not found: {exc}"}
    except Exception as exc:
        return {"status": "failed", "text": "", "detail": str(exc)}


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


__all__ = ["run_ocr", "run_ocr_from_screenshot"]
