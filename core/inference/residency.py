from __future__ import annotations

import os
from dataclasses import dataclass

from debug_utils import psutil, sentinel


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ResidencySnapshot:
    resident_enabled: bool
    host_ram_percent: float | None
    unload_ram_pct: float
    pressure_high: bool
    reason: str | None = None


class ResidencyMonitor:
    def __init__(self, *, resident_enabled: bool = True, unload_ram_pct: float = 85.0) -> None:
        self.resident_enabled = resident_enabled
        self.unload_ram_pct = unload_ram_pct

    @classmethod
    def from_env(cls) -> "ResidencyMonitor":
        return cls(
            resident_enabled=_env_bool("AI_LAN_LLAMACPP_RESIDENT", True),
            unload_ram_pct=_env_float("AI_LAN_LLAMACPP_UNLOAD_RAM_PCT", 85.0),
        )

    @sentinel
    def sample(self) -> ResidencySnapshot:
        if psutil is None:
            return ResidencySnapshot(
                resident_enabled=self.resident_enabled,
                host_ram_percent=None,
                unload_ram_pct=self.unload_ram_pct,
                pressure_high=False,
                reason="psutil_unavailable",
            )

        try:
            memory = psutil.virtual_memory()
            host_ram_percent = float(getattr(memory, "percent", 0.0))
        except Exception:
            return ResidencySnapshot(
                resident_enabled=self.resident_enabled,
                host_ram_percent=None,
                unload_ram_pct=self.unload_ram_pct,
                pressure_high=False,
                reason="memory_probe_failed",
            )

        return ResidencySnapshot(
            resident_enabled=self.resident_enabled,
            host_ram_percent=host_ram_percent,
            unload_ram_pct=self.unload_ram_pct,
            pressure_high=host_ram_percent >= self.unload_ram_pct,
            reason=None,
        )


__all__ = ["ResidencyMonitor", "ResidencySnapshot"]