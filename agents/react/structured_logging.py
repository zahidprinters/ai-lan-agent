from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AGENT_LOG_PATH = ROOT / "temp" / "logs" / "agent_reasoning.jsonl"
DEFAULT_TOOL_LOG_PATH = ROOT / "temp" / "logs" / "tool_events.jsonl"
DEFAULT_ERROR_LOG_PATH = ROOT / "temp" / "logs" / "runtime_errors.jsonl"


def _resolve_path(kind: str) -> Path:
    if kind == "agent":
        return Path(os.getenv("AI_LAN_AGENT_LOG_PATH", str(DEFAULT_AGENT_LOG_PATH)))
    if kind == "tool":
        return Path(os.getenv("AI_LAN_TOOL_LOG_PATH", str(DEFAULT_TOOL_LOG_PATH)))
    return Path(os.getenv("AI_LAN_ERROR_LOG_PATH", str(DEFAULT_ERROR_LOG_PATH)))


def append_structured_log(kind: str, payload: dict[str, object]) -> None:
    target = _resolve_path(kind)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


__all__ = [
    "DEFAULT_AGENT_LOG_PATH",
    "DEFAULT_ERROR_LOG_PATH",
    "DEFAULT_TOOL_LOG_PATH",
    "append_structured_log",
]