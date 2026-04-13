from __future__ import annotations

import json
import importlib
from pathlib import Path
import subprocess

import pytest
import tools.home.home_assistant as home_assistant

from router import dispatch_core as action_router
from router.router import parse_and_dispatch
from router.schema import ActionSchemaError, parse_agent_action
from router.dispatch_core import dispatch_agent_action
from tools.memory_store import add_memory_entry


@pytest.fixture(autouse=True)
def _reset_policy_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_LAN_POLICY_CONFIG_PATH", raising=False)

    import safety.policy_engine as pe

    importlib.reload(pe)
    monkeypatch.setattr(action_router, "evaluate_action_policy", pe.evaluate_action_policy)


def test_parse_agent_action_rejects_unknown_fields() -> None:
    payload = {
        "thought": "Search for current phase details.",
        "action": "web.search",
        "args": {"query": "AI Lan roadmap"},
        "safety_level": "low",
        "extra": True,
    }

    with pytest.raises(ActionSchemaError, match="Unknown action fields"):
        parse_agent_action(payload)


def test_dispatch_agent_action_executes_web_search(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    def fake_search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
        return [{"Title": "Roadmap", "Snippet": f"query={query} max={max_results}", "URL": "local"}]

    monkeypatch.setattr("router.dispatch_core.run_search", fake_search_web)
    monkeypatch.setitem(
        action_router.TOOL_REGISTRY,
        "web.search",
        action_router.ToolSpec(fake_search_web, ("query",), ("max_results",)),
    )

    result = dispatch_agent_action(
        {
            "thought": "Search for the current roadmap.",
            "action": "web.search",
            "args": {"query": "AI Lan roadmap", "max_results": 1},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert result.action == "web.search"
    assert result.observation == [
        {"Title": "Roadmap", "Snippet": "query=AI Lan roadmap max=1", "URL": "local"}
    ]
    audit_lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(audit_lines) == 1
    logged = json.loads(audit_lines[0])
    assert logged["result"]["status"] == "executed"


def test_dispatch_agent_action_rejects_shell_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    result = dispatch_agent_action(
        {
            "thought": "Run a shell command.",
            "action": "pc.execute_shell",
            "args": {"command": "dir"},
            "safety_level": "high",
        }
    )

    assert result.status == "rejected"
    assert "disabled" in result.policy_reason


def test_dispatch_agent_action_requires_confirmation_for_type_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    pending = dispatch_agent_action(
        {
            "thought": "Type the prepared message.",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        }
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "Type the prepared message.",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "executed"
    assert confirmed.observation is True


def test_dispatch_agent_action_pc_open_app_includes_verified_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setitem(
        action_router.TOOL_REGISTRY,
        "pc.open_app",
        action_router.ToolSpec(lambda app_name: f"opened {app_name}", ("app_name",)),
    )
    monkeypatch.setattr(
        "router.dispatch_core.list_running_apps",
        lambda limit=100: ["notepad.exe", "Code.exe"],
    )

    result = dispatch_agent_action(
        {
            "thought": "Open notepad.",
            "action": "pc.open_app",
            "args": {"app_name": "notepad"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["result"] == "opened notepad"
    assert result.observation["verification_status"] == "verified"
    assert "notepad" in result.observation["verification_detail"].lower()


def test_dispatch_agent_action_pc_open_app_not_verified_when_process_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setitem(
        action_router.TOOL_REGISTRY,
        "pc.open_app",
        action_router.ToolSpec(lambda app_name: f"opened {app_name}", ("app_name",)),
    )
    monkeypatch.setattr(
        "router.dispatch_core.list_running_apps",
        lambda limit=100: ["Code.exe", "python.exe"],
    )

    result = dispatch_agent_action(
        {
            "thought": "Open notepad.",
            "action": "pc.open_app",
            "args": {"app_name": "notepad"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["verification_status"] == "not_verified"
    assert "no running process matched" in result.observation["verification_detail"].lower()


def test_parse_and_dispatch_returns_structured_router_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    def fake_search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
        return [{"Title": query, "Snippet": "ok", "URL": "local"}]

    monkeypatch.setattr("router.dispatch_core.run_search", fake_search_web)
    monkeypatch.setitem(
        action_router.TOOL_REGISTRY,
        "web.search",
        action_router.ToolSpec(fake_search_web, ("query",), ("max_results",)),
    )

    result = parse_and_dispatch(
        {
            "thought": "Look up the roadmap.",
            "action": "web.search",
            "args": {"query": "roadmap"},
            "safety_level": "low",
        }
    )

    assert result["status"] == "executed"
    assert result["action"] == "web.search"
    assert result["observation"][0]["Title"] == "roadmap"


def test_dispatch_agent_action_executes_memory_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    db_path = tmp_path / "memory.sqlite3"
    add_memory_entry(
        kind="notes",
        content="Policy layer should gate typing actions with confirmation.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    result = dispatch_agent_action(
        {
            "thought": "Find policy notes about typing.",
            "action": "memory.search",
            "args": {"query": "typing confirmation", "db_path": str(db_path)},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert result.action == "memory.search"
    assert isinstance(result.observation, list)
    assert result.observation
    assert "typing actions" in result.observation[0]["summary"].lower()


def test_dispatch_agent_action_builds_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    db_path = tmp_path / "memory.sqlite3"
    merged_corpus_path = tmp_path / "merged.txt"
    merged_corpus_path.write_text(
        "Agent policy requires confirmation for risky typing actions.\n"
        "Ingestion pipeline merges trusted sources for cleaner context.\n",
        encoding="utf-8",
    )
    add_memory_entry(
        kind="notes",
        content="Confirmation is required before typing actions are executed.",
        metadata={"phase": 4},
        db_path=db_path,
    )

    result = dispatch_agent_action(
        {
            "thought": "Build context for typing safety.",
            "action": "context.build",
            "args": {
                "query": "typing confirmation policy",
                "db_path": str(db_path),
                "merged_corpus_path": str(merged_corpus_path),
                "memory_limit": 3,
                "snippet_limit": 3,
            },
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert result.action == "context.build"
    assert "context_text" in result.observation
    assert "Relevant Memory:" in result.observation["context_text"]
    assert "Relevant Corpus Snippets:" in result.observation["context_text"]


def test_dispatch_agent_action_pc_status_and_process_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    status_result = dispatch_agent_action(
        {
            "thought": "Collect machine status.",
            "action": "pc.get_system_status",
            "args": {},
            "safety_level": "low",
        }
    )
    apps_result = dispatch_agent_action(
        {
            "thought": "List active apps.",
            "action": "pc.list_running_apps",
            "args": {"limit": 5},
            "safety_level": "low",
        }
    )
    files_result = dispatch_agent_action(
        {
            "thought": "List files in docs folder.",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "docs", "limit": 5},
            "safety_level": "low",
        }
    )

    assert status_result.status == "executed"
    assert "platform" in status_result.observation
    assert apps_result.status == "executed"
    assert isinstance(apps_result.observation, list)
    assert files_result.status == "executed"
    assert files_result.observation["status"] == "ok"
    assert isinstance(files_result.observation["entries"], list)


def test_dispatch_agent_action_workspace_listing_blocks_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    result = dispatch_agent_action(
        {
            "thought": "Try listing outside workspace.",
            "action": "pc.list_workspace_files",
            "args": {"relative_path": "..", "limit": 5},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert result.observation["status"] == "blocked"


def test_dispatch_agent_action_android_requires_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    pending = dispatch_agent_action(
        {
            "thought": "Launch mobile app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        }
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "Launch mobile app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "executed"
    assert confirmed.observation["status"] in {"blocked_safe_mode", "blocked_policy", "ok", "failed"}


def test_dispatch_agent_action_android_launch_app_blocks_without_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.delenv("AI_LAN_ANDROID_ALLOWED_PACKAGES", raising=False)

    result = dispatch_agent_action(
        {
            "thought": "Launch mobile app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "blocked_policy"
    assert "AI_LAN_ANDROID_ALLOWED_PACKAGES" in result.observation["detail"]


def test_dispatch_agent_action_android_launch_app_runs_for_allowlisted_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOWED_PACKAGES", "com.example.app")

    def fake_run_adb(command: list[str], *, text: bool = True) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "com.example.app"
        return subprocess.CompletedProcess(command, 0, stdout="Starting: Intent", stderr="")

    monkeypatch.setattr("tools.android.adb.run_adb_command", fake_run_adb)
    monkeypatch.setattr(
        "router.dispatch_core.list_devices",
        lambda: [{"device_id": "emulator-5554", "status": "device", "detail": ""}],
    )

    result = dispatch_agent_action(
        {
            "thought": "Launch mobile app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "ok"
    assert result.observation["verification_status"] == "verified"


def test_dispatch_agent_action_android_launch_app_verification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOWED_PACKAGES", "com.example.app")

    def fake_run_adb(command: list[str], *, text: bool = True) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "com.example.app"
        return subprocess.CompletedProcess(command, 0, stdout="Starting: Intent", stderr="")

    monkeypatch.setattr("tools.android.adb.run_adb_command", fake_run_adb)

    def failing_list_devices() -> list[dict[str, str]]:
        raise RuntimeError("adb probe unavailable")

    monkeypatch.setattr("router.dispatch_core.list_devices", failing_list_devices)

    result = dispatch_agent_action(
        {
            "thought": "Launch mobile app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "ok"
    assert result.observation["verification_status"] == "verification_failed"
    assert "verification error" in result.observation["verification_detail"].lower()


def test_dispatch_agent_action_android_list_devices_low_risk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    result = dispatch_agent_action(
        {
            "thought": "List adb devices.",
            "action": "android.list_devices",
            "args": {},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert isinstance(result.observation, list)


def test_dispatch_agent_action_home_list_entities_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.delenv("AI_LAN_HOME_ASSISTANT_URL", raising=False)
    monkeypatch.delenv("AI_LAN_HOME_ASSISTANT_TOKEN", raising=False)

    result = dispatch_agent_action(
        {
            "thought": "List light entities.",
            "action": "home.list_entities",
            "args": {"domain": "light", "limit": 3},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert result.observation["status"] == "unavailable"
    assert result.observation["count"] == 0


def test_dispatch_agent_action_home_call_service_requires_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.delenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", raising=False)

    pending = dispatch_agent_action(
        {
            "thought": "Turn off the living room light.",
            "action": "home.call_service",
            "args": {
                "domain": "light",
                "service": "turn_off",
                "service_data": {"entity_id": "light.living_room"},
            },
            "safety_level": "medium",
        }
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "Turn off the living room light.",
            "action": "home.call_service",
            "args": {
                "domain": "light",
                "service": "turn_off",
                "service_data": {"entity_id": "light.living_room"},
            },
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "executed"
    assert confirmed.observation["status"] == "blocked_safe_mode"


def test_dispatch_agent_action_iot_reboot_node_requires_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.delenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", raising=False)

    pending = dispatch_agent_action(
        {
            "thought": "Reboot hallway node.",
            "action": "iot.reboot_node",
            "args": {"node_name": "hallway-node"},
            "safety_level": "medium",
        }
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "Reboot hallway node.",
            "action": "iot.reboot_node",
            "args": {"node_name": "hallway-node"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "executed"
    assert confirmed.observation["status"] == "blocked_safe_mode"


def test_dispatch_agent_action_home_call_service_blocks_without_service_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.delenv("AI_LAN_HOME_ALLOWED_SERVICES", raising=False)

    result = dispatch_agent_action(
        {
            "thought": "Turn on office light.",
            "action": "home.call_service",
            "args": {
                "domain": "light",
                "service": "turn_on",
                "service_data": {"entity_id": "light.office"},
            },
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "blocked_policy"
    assert "AI_LAN_HOME_ALLOWED_SERVICES" in result.observation["detail"]


def test_dispatch_agent_action_home_call_service_blocks_without_entity_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AI_LAN_HOME_ALLOWED_SERVICES", "light.turn_on")
    monkeypatch.delenv("AI_LAN_HOME_ALLOWED_ENTITIES", raising=False)

    result = dispatch_agent_action(
        {
            "thought": "Turn on office light.",
            "action": "home.call_service",
            "args": {
                "domain": "light",
                "service": "turn_on",
                "service_data": {"entity_id": "light.office"},
            },
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "blocked_policy"
    assert "AI_LAN_HOME_ALLOWED_ENTITIES" in result.observation["detail"]


def test_dispatch_agent_action_home_call_service_runs_for_allowlisted_service_and_entity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_HOME_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.setenv("AI_LAN_HOME_ALLOWED_SERVICES", "light.turn_on")
    monkeypatch.setenv("AI_LAN_HOME_ALLOWED_ENTITIES", "light.office")
    monkeypatch.setenv("AI_LAN_HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
    monkeypatch.setenv("AI_LAN_HOME_ASSISTANT_TOKEN", "local-token")

    monkeypatch.setattr(home_assistant, "_request_json", lambda *args, **kwargs: (200, [{"ok": True}]))

    result = dispatch_agent_action(
        {
            "thought": "Turn on office light.",
            "action": "home.call_service",
            "args": {
                "domain": "light",
                "service": "turn_on",
                "service_data": {"entity_id": "light.office"},
            },
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert result.status == "executed"
    assert result.observation["status"] == "ok"


def test_dispatch_agent_action_home_call_service_denied_by_policy_pack(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

        import safety.policy_engine as pe

        importlib.reload(pe)
        monkeypatch.setattr(action_router, "evaluate_action_policy", pe.evaluate_action_policy)

        result = dispatch_agent_action(
                {
                        "thought": "Unlock front door.",
                        "action": "home.call_service",
                        "args": {
                                "domain": "lock",
                                "service": "unlock",
                                "service_data": {"entity_id": "lock.front_door"},
                        },
                        "safety_level": "medium",
                },
                confirmed=True,
        )

        assert result.status == "rejected"
        assert "deny_home_services" in result.policy_reason


def test_dispatch_agent_action_iot_reboot_denied_by_policy_pack(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

        import safety.policy_engine as pe

        importlib.reload(pe)
        monkeypatch.setattr(action_router, "evaluate_action_policy", pe.evaluate_action_policy)

        result = dispatch_agent_action(
                {
                        "thought": "Reboot front door node.",
                        "action": "iot.reboot_node",
                        "args": {"node_name": "front-door-node"},
                        "safety_level": "medium",
                },
                confirmed=True,
        )

        assert result.status == "rejected"
        assert "deny_iot_nodes" in result.policy_reason
