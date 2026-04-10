from __future__ import annotations

from pathlib import Path

import pytest

from router.dispatch_core import dispatch_agent_action
from tools.web_ingest import IngestionSource, run_ingestion_pipeline


@pytest.mark.integration
def test_router_policy_adapter_android_launch_blocked_without_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS", "1")
    monkeypatch.delenv("AI_LAN_ANDROID_ALLOWED_PACKAGES", raising=False)

    pending = dispatch_agent_action(
        {
            "thought": "Try launching an Android app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        }
    )
    confirmed = dispatch_agent_action(
        {
            "thought": "Try launching an Android app.",
            "action": "android.launch_app",
            "args": {"package_name": "com.example.app"},
            "safety_level": "medium",
        },
        confirmed=True,
    )

    assert pending.status == "confirmation_required"
    assert confirmed.status == "executed"
    assert confirmed.observation["status"] == "blocked_policy"


@pytest.mark.integration
def test_router_policy_adapter_pc_process_listing_timeout_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS", "5")

    # Use subprocess.TimeoutExpired because adapter catches that exact exception type.
    import subprocess

    def timeout_run(*_: object, **__: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["tasklist"], timeout=5)

    monkeypatch.setattr("tools.system.host.subprocess.run", timeout_run)

    result = dispatch_agent_action(
        {
            "thought": "List running apps.",
            "action": "pc.list_running_apps",
            "args": {"limit": 5},
            "safety_level": "low",
        }
    )

    assert result.status == "executed"
    assert isinstance(result.observation, list)
    assert result.observation
    assert result.observation[0].startswith("unavailable:")
    assert "timed out" in result.observation[0]


@pytest.mark.integration
def test_ingestion_pipeline_enforces_trust_filtering(tmp_path: Path) -> None:
    sources = [
        IngestionSource(
            name="trusted-source",
            source_type="inline",
            location=(
                "Reliable source line one with detail.\n"
                "Reliable source line two with detail.\n"
                "Reliable source line three with detail."
            ),
            trust_score=0.9,
        ),
        IngestionSource(
            name="untrusted-source",
            source_type="inline",
            location="dup\ndup\n\x01bad",
            trust_score=0.1,
        ),
    ]

    merged_path = tmp_path / "merged.txt"
    report_path = tmp_path / "report.json"
    report = run_ingestion_pipeline(
        sources,
        merged_output_path=merged_path,
        report_output_path=report_path,
        min_final_score=0.5,
    )

    assert report.source_count == 2
    assert report.filtered_low_score_count == 1
    assert report.kept_count == 1
    assert [document.name for document in report.documents] == ["trusted-source"]
