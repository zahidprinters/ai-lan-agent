from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PROFILES = {
    "phi4_q4km": ROOT / "models" / "gguf" / "phi-4-mini-instruct-q4_k_m.gguf",
    "llama8b_q4km": ROOT / "models" / "gguf" / "llama-3.1-8b-instruct-q4_k_m.gguf",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_env_path(name: str) -> Path | None:
    raw = os.getenv(name, "").strip()
    return Path(raw) if raw else None


@dataclass(frozen=True)
class ModelSelection:
    model_path: Path | None
    task_complexity: str
    profile: str
    router_enabled: bool
    resident_enabled: bool
    selection_reason: str


@dataclass(frozen=True)
class ModelRoutingPlan:
    primary: ModelSelection
    candidates: list[ModelSelection]


class ReasoningModelRouter:
    def __init__(
        self,
        *,
        default_profile: str = "phi4_q4km",
        router_enabled: bool = False,
        resident_enabled: bool = True,
        simple_model_path: Path | None = None,
        complex_model_path: Path | None = None,
        explicit_model_path: Path | None = None,
    ) -> None:
        self.default_profile = default_profile
        self.router_enabled = router_enabled
        self.resident_enabled = resident_enabled
        self.simple_model_path = simple_model_path
        self.complex_model_path = complex_model_path
        self.explicit_model_path = explicit_model_path

    @classmethod
    def from_env(cls) -> "ReasoningModelRouter":
        return cls(
            default_profile=os.getenv("AI_LAN_LLAMACPP_MODEL_PROFILE", "phi4_q4km").strip().lower(),
            router_enabled=_env_bool("AI_LAN_MODEL_ROUTER_ENABLED", False),
            resident_enabled=_env_bool("AI_LAN_LLAMACPP_RESIDENT", True),
            simple_model_path=_resolve_env_path("AI_LAN_MODEL_ROUTER_SIMPLE_MODEL_PATH"),
            complex_model_path=_resolve_env_path("AI_LAN_MODEL_ROUTER_COMPLEX_MODEL_PATH"),
            explicit_model_path=_resolve_env_path("AI_LAN_LLAMACPP_MODEL_PATH"),
        )

    def _profile_path(self) -> Path | None:
        return DEFAULT_MODEL_PROFILES.get(self.default_profile)

    @staticmethod
    def _unique_paths(paths: list[Path | None]) -> list[Path | None]:
        seen: set[str] = set()
        unique: list[Path | None] = []
        for path in paths:
            if path is None:
                continue
            key = "" if path is None else str(path)
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        return unique

    def select_model(
        self,
        *,
        requested_model_path: str | Path | None = None,
        task_complexity: str = "complex",
        pressure_high: bool = False,
    ) -> ModelSelection:
        return self.build_plan(
            requested_model_path=requested_model_path,
            task_complexity=task_complexity,
            pressure_high=pressure_high,
        ).primary

    def build_plan(
        self,
        *,
        requested_model_path: str | Path | None = None,
        task_complexity: str = "complex",
        pressure_high: bool = False,
    ) -> ModelRoutingPlan:
        normalized_complexity = task_complexity.strip().lower() or "complex"

        if requested_model_path is not None:
            resident_enabled = False if pressure_high else self.resident_enabled
            selection = ModelSelection(
                model_path=Path(requested_model_path),
                task_complexity=normalized_complexity,
                profile=self.default_profile,
                router_enabled=self.router_enabled,
                resident_enabled=resident_enabled,
                selection_reason="explicit_request_pressure" if pressure_high else "explicit_request",
            )
            return ModelRoutingPlan(primary=selection, candidates=[selection])

        if self.explicit_model_path is not None:
            resident_enabled = False if pressure_high else self.resident_enabled
            selection = ModelSelection(
                model_path=self.explicit_model_path,
                task_complexity=normalized_complexity,
                profile=self.default_profile,
                router_enabled=self.router_enabled,
                resident_enabled=resident_enabled,
                selection_reason="env_model_path_pressure" if pressure_high else "env_model_path",
            )
            return ModelRoutingPlan(primary=selection, candidates=[selection])

        profile_path = self._profile_path()
        if pressure_high:
            ordered_paths = self._unique_paths(
                [self.simple_model_path, profile_path, self.complex_model_path]
            )
            selection_reason = "pressure_simple_route"
            resident_enabled = False
        elif self.router_enabled and normalized_complexity == "simple":
            ordered_paths = self._unique_paths(
                [self.simple_model_path, self.complex_model_path, profile_path]
            )
            selection_reason = "simple_route"
            resident_enabled = self.resident_enabled
        elif self.router_enabled:
            ordered_paths = self._unique_paths(
                [self.complex_model_path, self.simple_model_path, profile_path]
            )
            selection_reason = "complex_route"
            resident_enabled = self.resident_enabled
        else:
            ordered_paths = self._unique_paths([profile_path, self.simple_model_path, self.complex_model_path])
            selection_reason = "profile_default"
            resident_enabled = self.resident_enabled

        candidates: list[ModelSelection] = []
        for index, path in enumerate(ordered_paths):
            reason = selection_reason if index == 0 else f"{selection_reason}_fallback_{index}"
            candidates.append(
                ModelSelection(
                    model_path=path,
                    task_complexity=normalized_complexity,
                    profile=self.default_profile,
                    router_enabled=self.router_enabled,
                    resident_enabled=resident_enabled,
                    selection_reason=reason,
                )
            )

        if not candidates:
            candidates.append(
                ModelSelection(
                    model_path=None,
                    task_complexity=normalized_complexity,
                    profile=self.default_profile,
                    router_enabled=self.router_enabled,
                    resident_enabled=resident_enabled,
                    selection_reason="profile_default",
                )
            )

        return ModelRoutingPlan(primary=candidates[0], candidates=candidates)


__all__ = ["DEFAULT_MODEL_PROFILES", "ModelRoutingPlan", "ModelSelection", "ReasoningModelRouter"]