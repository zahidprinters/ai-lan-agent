"""Observation formatting placeholder."""


def to_observation_text(result: dict[str, object]) -> str:
    return str(result.get("observation", ""))
