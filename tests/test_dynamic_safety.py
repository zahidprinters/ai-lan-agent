from __future__ import annotations

import importlib

import pytest

from router.schema import parse_agent_action


@pytest.mark.unit
def test_sensitive_context_requires_strong_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "project_name: AI Lan",
                "mode: safe",
                "default_device: cpu",
                "dynamic_safety_enabled: true",
                'sensitive_context_keywords: "password,otp,bank"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(settings_path))

    import safety.policy_engine as pe

    importlib.reload(pe)

    action = parse_agent_action(
        {
            "thought": "Type a code.",
            "action": "pc.type_text",
            "args": {"text": "123456"},
            "safety_level": "medium",
        }
    )
    decision = pe.evaluate_action_policy(action, policy_context={"sensitive_context": True})

    assert decision.allowed
    assert decision.requires_confirmation
    assert decision.requires_strong_confirmation
    assert "strong confirmation" in decision.reason.lower()


@pytest.mark.unit
def test_non_sensitive_context_keeps_existing_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "project_name: AI Lan",
                "mode: safe",
                "default_device: cpu",
                "dynamic_safety_enabled: true",
                'sensitive_context_keywords: "password,otp,bank"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(settings_path))

    import safety.policy_engine as pe

    importlib.reload(pe)

    action = parse_agent_action(
        {
            "thought": "Type a greeting.",
            "action": "pc.type_text",
            "args": {"text": "hello"},
            "safety_level": "medium",
        }
    )
    decision = pe.evaluate_action_policy(
        action,
        policy_context={"sensitive_context": False, "perception_summary": "home dashboard"},
    )

    assert decision.allowed
    assert decision.requires_confirmation
    assert not decision.requires_strong_confirmation


@pytest.mark.unit
def test_runtime_context_sets_sensitive_flag_from_perception_keywords(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "project_name: AI Lan",
                "mode: safe",
                "default_device: cpu",
                "dynamic_safety_enabled: true",
                'sensitive_context_keywords: "password,otp,bank"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(settings_path))

    import runtime.context as rc

    monkeypatch.setattr(
        rc,
        "build_prompt_context",
        lambda **kwargs: {"context_text": "retrieved context", "query": kwargs.get("query", "")},
    )

    context = rc.build_runtime_context(
        query="help with account",
        perception_summary="Bank login page asks for password and otp",
    )

    assert context["sensitive_context"] is True


@pytest.mark.unit
def test_dispatch_requires_strong_confirmation_when_sensitive(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "project_name: AI Lan",
                "mode: safe",
                "default_device: cpu",
                "dynamic_safety_enabled: true",
                'sensitive_context_keywords: "password,otp,bank"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LAN_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("AI_LAN_ACTION_AUDIT_PATH", str(tmp_path / "audit.jsonl"))

    import safety.policy_engine as pe
    import router.dispatch_core as dc

    importlib.reload(pe)
    dc.evaluate_action_policy = pe.evaluate_action_policy

    result = dc.dispatch_agent_action(
        {
            "thought": "Type OTP.",
            "action": "pc.type_text",
            "args": {"text": "123456"},
            "safety_level": "medium",
        },
        policy_context={"sensitive_context": True, "perception_summary": "otp prompt"},
    )

    assert result.status == "confirmation_required"
    assert "strong confirmation" in result.policy_reason.lower()
