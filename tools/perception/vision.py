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

    @sentinel
    def capture_once(self, *, min_confidence: float = 45.0) -> VisionCaptureSample:
        _configure_tesseract()
        screenshot_path = self._capture_screenshot()
        extraction = run_ocr_with_confidence(str(screenshot_path), min_confidence=min_confidence)
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
        )

    @sentinel
    def sample_bounded(
        self,
        *,
        max_samples: int = 1,
        min_confidence: float = 45.0,
    ) -> list[VisionCaptureSample]:
        bounded_samples = max(1, min(5, int(max_samples)))
        samples: list[VisionCaptureSample] = []
        for _ in range(bounded_samples):
            samples.append(self.capture_once(min_confidence=min_confidence))
        return samples


_DEFAULT_CAPTURE_SERVICE = VisionCaptureService()


@sentinel
def capture_vision_sample(
    *,
    min_confidence: float = 45.0,
    max_samples: int = 1,
) -> dict[str, object]:
    samples = _DEFAULT_CAPTURE_SERVICE.sample_bounded(
        max_samples=max_samples,
        min_confidence=min_confidence,
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
