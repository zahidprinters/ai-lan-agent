import mss
import pytesseract
from PIL import Image
from pathlib import Path
from debug_utils import sentinel

from tools.perception.ocr import _configure_tesseract


@sentinel
def capture_screen_text() -> str:
    """Captures a screenshot and extracts text using OCR."""
    _configure_tesseract()
    temp_dir = Path("temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = temp_dir / "screen.png"

    try:
        with mss.mss() as sct:
            sct.shot(output=str(screenshot_path))

        text = pytesseract.image_to_string(Image.open(screenshot_path))
        return text.strip()
    except Exception as exc:
        return f"Vision perception error: {exc}"


__all__ = ["capture_screen_text"]
