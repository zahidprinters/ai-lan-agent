from __future__ import annotations

import pytest
from runtime.session import VALID_DEVICE_TYPES, RuntimeSession


# ---------------------------------------------------------------------------
# RuntimeSession
# ---------------------------------------------------------------------------

def test_runtime_session_defaults() -> None:
    s = RuntimeSession()
    assert s.device_type == "cli"
    assert s.profile == "default"
    assert len(s.session_id) == 36  # uuid4 with hyphens
    assert s.started_at.endswith("+00:00") or s.started_at.endswith("Z") or "T" in s.started_at


def test_runtime_session_to_dict_keys() -> None:
    s = RuntimeSession(device_type="companion", profile="work")
    d = s.to_dict()
    assert d["device_type"] == "companion"
    assert d["profile"] == "work"
    assert "session_id" in d
    assert "started_at" in d


def test_runtime_session_invalid_device_type_falls_back_to_cli() -> None:
    s = RuntimeSession(device_type="fridge")
    assert s.device_type == "cli"


def test_runtime_session_empty_profile_falls_back_to_default() -> None:
    s = RuntimeSession(profile="   ")
    assert s.profile == "default"


def test_runtime_session_all_valid_device_types() -> None:
    for device_type in VALID_DEVICE_TYPES:
        s = RuntimeSession(device_type=device_type)
        assert s.device_type == device_type


def test_runtime_session_unique_ids() -> None:
    ids = {RuntimeSession().session_id for _ in range(10)}
    assert len(ids) == 10


# ---------------------------------------------------------------------------
# ChatSession device_type and profile fields
# ---------------------------------------------------------------------------

def test_chat_session_device_type_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_LAN_DEVICE_TYPE", raising=False)
    monkeypatch.delenv("AI_LAN_PROFILE", raising=False)
    from runtime.chat_interface import ChatSession
    s = ChatSession()
    assert s.device_type == "cli"
    assert s.profile == "default"


def test_chat_session_explicit_device_type_and_profile() -> None:
    from runtime.chat_interface import ChatSession
    s = ChatSession(device_type="companion", profile="work")
    assert s.device_type == "companion"
    assert s.profile == "work"


def test_chat_session_get_state_includes_surface_fields() -> None:
    from runtime.chat_interface import ChatSession
    s = ChatSession(device_type="satellite", profile="home")
    state = s.get_state()
    assert state["device_type"] == "satellite"
    assert state["profile"] == "home"


# ---------------------------------------------------------------------------
# Launcher parser
# ---------------------------------------------------------------------------

def test_launcher_parser_all_modes() -> None:
    from scripts.launch import build_parser
    parser = build_parser()
    for mode in ("cli", "voice", "web", "api", "companion", "satellite"):
        args = parser.parse_args(["--mode", mode])
        assert args.mode == mode


def test_launcher_parser_companion_default_mode() -> None:
    from scripts.launch import build_parser
    parser = build_parser()
    args = parser.parse_args(["--mode", "companion"])
    assert args.mode == "companion"
    assert args.port is None  # resolved to 8766 at runtime


def test_launcher_parser_profile_arg() -> None:
    from scripts.launch import build_parser
    parser = build_parser()
    args = parser.parse_args(["--mode", "api", "--profile", "work"])
    assert args.profile == "work"


def test_launcher_mode_default_ports() -> None:
    from scripts.launch import _MODE_DEFAULT_PORTS
    assert _MODE_DEFAULT_PORTS["companion"] == 8766
    assert _MODE_DEFAULT_PORTS["satellite"] == 8767
    assert _MODE_DEFAULT_PORTS["api"] == 8765
