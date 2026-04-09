"""Short-term conversation buffer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class BufferMessage:
    role: str
    message: str


class ShortTermBuffer:
    def __init__(self, max_items: int = 20) -> None:
        self._items: deque[BufferMessage] = deque(maxlen=max_items)

    def add(self, message: str, role: str = "user") -> None:
        normalized_role = role.strip() or "user"
        normalized_message = message.strip()
        if not normalized_message:
            return
        self._items.append(BufferMessage(role=normalized_role, message=normalized_message))

    def get_all(self) -> list[BufferMessage]:
        return list(self._items)

    def get_messages(self, *, role: str | None = None) -> list[BufferMessage]:
        if role is None:
            return self.get_all()
        return [item for item in self._items if item.role == role]

    def to_context_text(self, limit: int = 12) -> str:
        selected = list(self._items)[-max(limit, 1) :]
        if not selected:
            return "(no short-term context)"
        return "\n".join(f"{item.role}: {item.message}" for item in selected)
