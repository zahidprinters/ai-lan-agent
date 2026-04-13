from __future__ import annotations

"""Lightweight runtime session identity for multi-surface tracking."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

VALID_DEVICE_TYPES: frozenset[str] = frozenset(
    {"cli", "voice", "web", "api", "companion", "satellite"}
)


@dataclass
class RuntimeSession:
    """Tracks surface identity for a single AI Lan session.

    Attributes:
        device_type: The surface this session is running on (cli/voice/web/api/companion/satellite).
        profile: Optional user context segment name (default "default").
        session_id: Auto-generated UUID-based identifier.
        started_at: ISO timestamp of session creation.
    """

    device_type: str = "cli"
    profile: str = "default"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def __post_init__(self) -> None:
        normalized_type = self.device_type.strip().lower()
        self.device_type = normalized_type if normalized_type in VALID_DEVICE_TYPES else "cli"
        normalized_profile = self.profile.strip()
        self.profile = normalized_profile if normalized_profile else "default"

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "device_type": self.device_type,
            "profile": self.profile,
            "started_at": self.started_at,
        }


__all__ = ["VALID_DEVICE_TYPES", "RuntimeSession"]

