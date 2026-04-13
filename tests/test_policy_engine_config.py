from __future__ import annotations

import importlib

import pytest

from router.schema import parse_agent_action


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


@pytest.mark.unit
def test_policy_engine_loads_home_service_policy_packs(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
policy:
  allow_actions:
    - home.call_service
  deny_actions: []
  require_confirmation:
    - home.call_service
  allow_home_services:
    - lock.lock
  deny_home_services:
    - lock.unlock
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(policy_file))

    import safety.policy_engine as pe

    importlib.reload(pe)

    assert "lock.lock" in pe.HOME_ALLOWED_SERVICES
    assert "lock.unlock" in pe.HOME_DENIED_SERVICES


@pytest.mark.unit
def test_policy_engine_denies_home_service_from_domain_pack(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
policy:
  allow_actions:
    - home.call_service
  deny_actions: []
  require_confirmation:
    - home.call_service
  allow_home_services:
    - lock.lock
  deny_home_services:
    - lock.unlock
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(policy_file))

    import safety.policy_engine as pe

    importlib.reload(pe)

    denied_action = parse_agent_action(
        {
            "thought": "Unlock the front door.",
            "action": "home.call_service",
            "args": {
                "domain": "lock",
                "service": "unlock",
                "service_data": {"entity_id": "lock.front_door"},
            },
            "safety_level": "medium",
        }
    )
    allowed_action = parse_agent_action(
        {
            "thought": "Lock the front door.",
            "action": "home.call_service",
            "args": {
                "domain": "lock",
                "service": "lock",
                "service_data": {"entity_id": "lock.front_door"},
            },
            "safety_level": "medium",
        }
    )

    denied_decision = pe.evaluate_action_policy(denied_action)
    allowed_decision = pe.evaluate_action_policy(allowed_action)

    assert not denied_decision.allowed
    assert "deny_home_services" in denied_decision.reason
    assert allowed_decision.allowed
    assert allowed_decision.requires_confirmation


@pytest.mark.unit
def test_policy_engine_loads_iot_node_policy_packs(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
policy:
  allow_actions:
    - iot.reboot_node
  deny_actions: []
  require_confirmation:
    - iot.reboot_node
  allow_iot_nodes:
    - hallway-node
  deny_iot_nodes:
    - front-door-node
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(policy_file))

    import safety.policy_engine as pe

    importlib.reload(pe)

    assert "hallway-node" in pe.IOT_ALLOWED_NODES
    assert "front-door-node" in pe.IOT_DENIED_NODES


@pytest.mark.unit
def test_policy_engine_enforces_iot_node_policy_packs(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
policy:
  allow_actions:
    - iot.reboot_node
  deny_actions: []
  require_confirmation:
    - iot.reboot_node
  allow_iot_nodes:
    - hallway-node
  deny_iot_nodes:
    - front-door-node
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("AI_LAN_POLICY_CONFIG_PATH", str(policy_file))

    import safety.policy_engine as pe

    importlib.reload(pe)

    denied_action = parse_agent_action(
        {
            "thought": "Reboot front door node.",
            "action": "iot.reboot_node",
            "args": {"node_name": "front-door-node"},
            "safety_level": "medium",
        }
    )
    blocked_unknown_action = parse_agent_action(
        {
            "thought": "Reboot unknown node.",
            "action": "iot.reboot_node",
            "args": {"node_name": "kitchen-node"},
            "safety_level": "medium",
        }
    )
    allowed_action = parse_agent_action(
        {
            "thought": "Reboot hallway node.",
            "action": "iot.reboot_node",
            "args": {"node_name": "hallway-node"},
            "safety_level": "medium",
        }
    )

    denied_decision = pe.evaluate_action_policy(denied_action)
    blocked_unknown_decision = pe.evaluate_action_policy(blocked_unknown_action)
    allowed_decision = pe.evaluate_action_policy(allowed_action)

    assert not denied_decision.allowed
    assert "deny_iot_nodes" in denied_decision.reason
    assert not blocked_unknown_decision.allowed
    assert "allow_iot_nodes" in blocked_unknown_decision.reason
    assert allowed_decision.allowed
    assert allowed_decision.requires_confirmation
