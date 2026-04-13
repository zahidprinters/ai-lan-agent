"""ESPHome tool facade with deterministic safe-mode behavior."""

from __future__ import annotations

import os

from debug_utils import sentinel


def _configured_nodes() -> list[str]:
    raw = os.getenv("AI_LAN_ESPHOME_NODES", "")
    nodes = [entry.strip() for entry in raw.split(",")]
    return [node for node in nodes if node]


def _allowed_nodes() -> set[str]:
    raw = os.getenv("AI_LAN_ESPHOME_ALLOWED_NODES", "")
    nodes = {entry.strip() for entry in raw.split(",") if entry.strip()}
    return {node.lower() for node in nodes}


def _allow_side_effects() -> bool:
    return os.getenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@sentinel
def list_nodes() -> dict[str, object]:
    nodes = _configured_nodes()
    if not nodes:
        return {
            "status": "unavailable",
            "detail": "Set AI_LAN_ESPHOME_NODES to expose known ESPHome nodes.",
            "nodes": [],
        }
    return {"status": "ok", "detail": "", "nodes": nodes}


@sentinel
def reboot_node(node_name: str) -> dict[str, str]:
    normalized = node_name.strip()
    if not normalized:
        return {"status": "failed", "detail": "node_name is required."}

    if not _allow_side_effects():
        return {
            "status": "blocked_safe_mode",
            "detail": "Set AI_LAN_HOME_ALLOW_SIDE_EFFECTS=1 to enable ESPHome side-effect actions.",
        }

    allowed = _allowed_nodes()
    if allowed and normalized.lower() not in allowed:
        return {
            "status": "blocked_policy",
            "detail": "Node is not in AI_LAN_ESPHOME_ALLOWED_NODES allowlist.",
        }

    return {
        "status": "queued_stub",
        "detail": "ESPHome reboot action accepted by policy but adapter execution is still a safe stub.",
    }


__all__ = ["list_nodes", "reboot_node"]
