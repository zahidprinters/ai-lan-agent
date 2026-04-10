from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_policy_engine_loads_action_sets_from_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
policy:
  allow_actions:
    - web.search
  deny_actions:
    - web.browser_fetch
  require_confirmation:
    - web.search
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(policy_file))

    import safety.policy_engine as pe

    importlib.reload(pe)

    assert "web.search" in pe.ALLOWED_ACTIONS
    assert "web.browser_fetch" in pe.DENIED_ACTIONS
    assert "web.search" in pe.CONFIRMATION_REQUIRED_ACTIONS


@pytest.mark.unit
def test_policy_engine_uses_defaults_when_file_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", "temp/does_not_exist_policies.yaml")

    import safety.policy_engine as pe

    importlib.reload(pe)

    assert "web.search" in pe.ALLOWED_ACTIONS
    assert "pc.execute_shell" in pe.DENIED_ACTIONS
