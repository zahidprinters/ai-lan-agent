"""Per-session ReAct state container."""

from dataclasses import dataclass, field


@dataclass
class ReactState:
    thoughts: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    reflection_retries_used: int = 0
