import mss
from pathlib import Path
from dataclasses import asdict, dataclass
from debug_utils import sentinel

from tools.perception.ocr import _configure_tesseract
from tools.perception.ocr import run_ocr_with_confidence


@dataclass(frozen=True)
class VisionCaptureSample:
    status: str
    text: str
    filtered_text: str
    average_confidence: float | None
    detail: str
    screenshot_path: str
    preprocessed_path: str | None = None
    ocr_backend: str = "tesseract"
    source: str = "screen_ocr"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class VisionCaptureService:
    """Capture screen snapshots and run confidence-filtered OCR extraction."""

    def __init__(
        self,
        *,
        output_dir: Path | None = None,
        screenshot_name: str = "screen.png",
    ) -> None:
        self.output_dir = output_dir or Path("temp") / "vision"
        self.screenshot_name = screenshot_name

    def _capture_screenshot(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = self.output_dir / self.screenshot_name
        with mss.mss() as sct:
            sct.shot(output=str(screenshot_path))
        return screenshot_path

    def _preprocess_for_ocr(self, screenshot_path: Path) -> Path:
        processed_path = screenshot_path.with_name(f"{screenshot_path.stem}_processed.png")
        try:
            import cv2  # type: ignore[import-untyped]

            image = cv2.imread(str(screenshot_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                return screenshot_path
            denoised = cv2.GaussianBlur(image, (3, 3), 0)
            _, thresholded = cv2.threshold(
                denoised,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
            cv2.imwrite(str(processed_path), thresholded)
            return processed_path
        except Exception:
            return screenshot_path

    @sentinel
    def capture_once(
        self,
        *,
        min_confidence: float = 45.0,
        ocr_backend: str = "auto",
        enable_easyocr_fallback: bool = True,
        preprocess_for_ocr: bool = True,
    ) -> VisionCaptureSample:
        _configure_tesseract()
        screenshot_path = self._capture_screenshot()
        ocr_input_path = (
            self._preprocess_for_ocr(screenshot_path)
            if preprocess_for_ocr
            else screenshot_path
        )
        extraction = run_ocr_with_confidence(
            str(ocr_input_path),
            min_confidence=min_confidence,
            backend=ocr_backend,
            enable_easyocr_fallback=enable_easyocr_fallback,
        )
        return VisionCaptureSample(
            status=str(extraction.get("status", "failed")),
            text=str(extraction.get("text", "")).strip(),
            filtered_text=str(extraction.get("filtered_text", "")).strip(),
            average_confidence=(
                float(extraction["average_confidence"])
                if extraction.get("average_confidence") is not None
                else None
            ),
            detail=str(extraction.get("detail", "")).strip(),
            screenshot_path=str(screenshot_path),
            preprocessed_path=(
                str(ocr_input_path) if ocr_input_path != screenshot_path else None
            ),
            ocr_backend=str(extraction.get("backend", "tesseract")).strip() or "tesseract",
        )

    @sentinel
    def sample_bounded(
        self,
        *,
        max_samples: int = 1,
        min_confidence: float = 45.0,
        ocr_backend: str = "auto",
        enable_easyocr_fallback: bool = True,
        preprocess_for_ocr: bool = True,
    ) -> list[VisionCaptureSample]:
        bounded_samples = max(1, min(5, int(max_samples)))
        samples: list[VisionCaptureSample] = []
        for _ in range(bounded_samples):
            samples.append(
                self.capture_once(
                    min_confidence=min_confidence,
                    ocr_backend=ocr_backend,
                    enable_easyocr_fallback=enable_easyocr_fallback,
                    preprocess_for_ocr=preprocess_for_ocr,
                )
            )
        return samples


_DEFAULT_CAPTURE_SERVICE = VisionCaptureService()


@sentinel
def capture_vision_sample(
    *,
    min_confidence: float = 45.0,
    max_samples: int = 1,
    ocr_backend: str = "auto",
    enable_easyocr_fallback: bool = True,
    preprocess_for_ocr: bool = True,
) -> dict[str, object]:
    samples = _DEFAULT_CAPTURE_SERVICE.sample_bounded(
        max_samples=max_samples,
        min_confidence=min_confidence,
        ocr_backend=ocr_backend,
        enable_easyocr_fallback=enable_easyocr_fallback,
        preprocess_for_ocr=preprocess_for_ocr,
    )
    best = max(samples, key=lambda sample: sample.average_confidence or -1.0)
    payload = best.to_dict()
    payload["sample_count"] = len(samples)
    return payload


@sentinel
def capture_screen_text() -> str:
    """Captures a screenshot and extracts text using OCR."""
    try:
        sample = capture_vision_sample(min_confidence=45.0, max_samples=1)
        filtered = str(sample.get("filtered_text", "")).strip()
        raw = str(sample.get("text", "")).strip()
        return filtered or raw
    except Exception as exc:
        return f"Vision perception error: {exc}"


__all__ = [
    "VisionCaptureSample",
    "VisionCaptureService",
    "capture_screen_text",
    "capture_vision_sample",
]
