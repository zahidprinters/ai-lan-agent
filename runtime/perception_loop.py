from __future__ import annotations

"""Low-frequency perception loop for embodied context awareness."""

import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from debug_utils import sentinel
from tools.perception.vision import capture_screen_text


@dataclass(frozen=True)
class PerceptionSnapshot:
    timestamp: str
    summary: str
    source: str = "screen_ocr"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _summarize_ocr_text(text: str, limit: int = 400) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "(no text detected)"
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


class PerceptionLoop:
    """Background OCR sampler that emits compact situational context snapshots."""

    def __init__(
        self,
        *,
        interval_sec: int = 10,
        max_interval_sec: int = 30,
        adaptive: bool = True,
        backoff_multiplier: float = 1.5,
        on_snapshot: Callable[[PerceptionSnapshot], None] | None = None,
    ) -> None:
        self.interval_sec = max(1, int(interval_sec))
        self.max_interval_sec = max(self.interval_sec, int(max_interval_sec))
        self.adaptive = adaptive
        self.backoff_multiplier = max(1.1, float(backoff_multiplier))
        self.on_snapshot = on_snapshot
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_snapshot: PerceptionSnapshot | None = None
        self._current_interval_sec = self.interval_sec

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_snapshot(self) -> PerceptionSnapshot | None:
        return self._last_snapshot

    @property
    def current_interval_sec(self) -> int:
        return self._current_interval_sec

    @sentinel
    def collect_once(self) -> PerceptionSnapshot:
        previous_summary = self._last_snapshot.summary if self._last_snapshot is not None else None
        text = capture_screen_text()
        snapshot = PerceptionSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=_summarize_ocr_text(text),
        )

        if self.adaptive and previous_summary is not None:
            if snapshot.summary == previous_summary:
                next_interval = int(round(self._current_interval_sec * self.backoff_multiplier))
                self._current_interval_sec = min(self.max_interval_sec, max(self.interval_sec, next_interval))
            else:
                self._current_interval_sec = self.interval_sec

        self._last_snapshot = snapshot
        if self.on_snapshot:
            self.on_snapshot(snapshot)
        return snapshot

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.collect_once()
            except Exception:
                # Keep perception loop resilient; errors should not kill runtime.
                pass
            self._stop_event.wait(self._current_interval_sec)

    @sentinel
    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._current_interval_sec = self.interval_sec
        self._thread = threading.Thread(target=self._run, name="ai-lan-perception", daemon=True)
        self._thread.start()

    @sentinel
    def stop(self, timeout_sec: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_sec)


__all__ = ["PerceptionLoop", "PerceptionSnapshot"]
