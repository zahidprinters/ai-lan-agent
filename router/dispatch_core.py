from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from debug_utils import sentinel

from memory.long_term.retrieval import retrieve_relevant_memories
from router.schema import AgentAction, ActionSchemaError, parse_agent_action
from safety.policy_engine import evaluate_action_policy
from tools.android.adb import launch_app, list_devices
from tools.android.input import swipe_screen, tap_screen
from tools.android.screen import capture_screenshot
from tools.android.scrcpy import start_mirror
from tools.perception.ocr import run_ocr, run_ocr_from_screenshot
from tools.perception.vision import capture_screen_text
from tools.context_builder import build_prompt_context
from tools.desktop.keyboard import type_text
from tools.system.clipboard import read_clipboard
from tools.system.files import list_workspace_files
from tools.system.host import (
    get_system_status,
    list_running_apps,
    open_app,
)
from tools.web.browser import browser_fetch
from tools.web.search import run_search

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ToolSpec:
    handler: Callable[..., object]
    required_args: tuple[str, ...]
    optional_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionExecutionResult:
    status: str
    action: str
    observation: Any
    policy_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    status: str
    detail: str


@sentinel
def _memory_search_tool(
    query: str,
    limit: int = 5,
    min_score: float = 0.05,
    kind: str | None = None,
    db_path: str | None = None,
    memory_backend: str | None = None,
    chroma_path: str | None = None,
) -> list[dict[str, object]]:
    hits = retrieve_relevant_memories(
        query=query,
        limit=limit,
        min_score=min_score,
        kind=kind,
        db_path=Path(db_path) if db_path else None,
        memory_backend=memory_backend,
        chroma_path=Path(chroma_path) if chroma_path else None,
    )
    return [hit.to_dict() for hit in hits]


@sentinel
def _context_build_tool(
    query: str,
    memory_limit: int = 5,
    snippet_limit: int = 5,
    min_score: float = 0.05,
    memory_kind: str | None = None,
    db_path: str | None = None,
    memory_backend: str | None = None,
    chroma_path: str | None = None,
    merged_corpus_path: str | None = None,
) -> dict[str, object]:
    return build_prompt_context(
        query=query,
        memory_limit=memory_limit,
        snippet_limit=snippet_limit,
        min_score=min_score,
        memory_kind=memory_kind,
        memory_db_path=Path(db_path) if db_path else None,
        memory_backend=memory_backend,
        chroma_path=Path(chroma_path) if chroma_path else None,
        merged_corpus_path=Path(merged_corpus_path) if merged_corpus_path else None,
    )


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "web.search": ToolSpec(run_search, ("query",), ("max_results",)),
    "memory.search": ToolSpec(
        _memory_search_tool,
        ("query",),
        ("limit", "min_score", "kind", "db_path", "memory_backend", "chroma_path"),
    ),
    "context.build": ToolSpec(
        _context_build_tool,
        ("query",),
        (
            "memory_limit",
            "snippet_limit",
            "min_score",
            "memory_kind",
            "db_path",
            "memory_backend",
            "chroma_path",
            "merged_corpus_path",
        ),
    ),
    "pc.type_text": ToolSpec(type_text, ("text",)),
    "pc.open_app": ToolSpec(open_app, ("app_name",)),
    "pc.read_clipboard": ToolSpec(read_clipboard, ()),
    "pc.get_system_status": ToolSpec(get_system_status, ()),
    "pc.list_running_apps": ToolSpec(list_running_apps, (), ("limit",)),
    "pc.list_workspace_files": ToolSpec(
        list_workspace_files, (), ("relative_path", "limit", "include_hidden")
    ),
    "android.list_devices": ToolSpec(list_devices, ()),
    "android.launch_app": ToolSpec(launch_app, ("package_name",), ("activity", "device_id")),
    "android.tap": ToolSpec(tap_screen, ("x", "y"), ("device_id",)),
    "android.swipe": ToolSpec(swipe_screen, ("x1", "y1", "x2", "y2"), ("duration_ms", "device_id")),
    "android.capture_screenshot": ToolSpec(capture_screenshot, (), ("output_path", "device_id")),
    "pc.inspect_screen": ToolSpec(capture_screen_text, ()),
    "web.browser_fetch": ToolSpec(browser_fetch, ("url",), ("screenshot_path", "timeout_ms")),
    "pc.ocr_image": ToolSpec(run_ocr, ("image_path",)),
    "pc.ocr_screen": ToolSpec(run_ocr_from_screenshot, ()),
    "android.scrcpy_mirror": ToolSpec(
        start_mirror, (), ("device_id", "max_bitrate", "max_fps", "no_control")
    ),
}


def _normalize_process_name(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.endswith(".exe"):
        return normalized[:-4]
    return normalized


@sentinel
def _verify_pc_open_app(action: AgentAction, observation: object) -> VerificationResult:
    _ = observation
    app_name = str(action.args.get("app_name", "")).strip()
    if not app_name:
        return VerificationResult("verification_failed", "Missing app_name for verification.")

    running = list_running_apps(limit=100)
    if running and str(running[0]).startswith("unavailable:"):
        return VerificationResult("verification_failed", str(running[0]))

    target = _normalize_process_name(app_name)
    matches = []
    for item in running:
        candidate = _normalize_process_name(str(item))
        if target == candidate or target in candidate or candidate in target:
            matches.append(str(item))

    if matches:
        detail = f"Verified running app match for '{app_name}': {matches[0]}"
        return VerificationResult("verified", detail)

    return VerificationResult(
        "not_verified", f"No running process matched requested app '{app_name}'."
    )


@sentinel
def _verify_android_launch_app(action: AgentAction, observation: object) -> VerificationResult:
    if not isinstance(observation, dict):
        return VerificationResult(
            "verification_failed", "Launch observation was not a structured object."
        )

    launch_status = str(observation.get("status", "")).strip().lower()
    launch_detail = str(observation.get("detail", "")).strip()
    if launch_status != "ok":
        detail = launch_detail or f"Launch returned status '{launch_status or 'unknown'}'."
        return VerificationResult("not_verified", detail)

    devices = list_devices()
    available = [
        item
        for item in devices
        if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "device"
    ]
    if not available:
        unavailable = next(
            (
                str(item.get("detail", "")).strip() or str(item.get("status", "")).strip()
                for item in devices
                if isinstance(item, dict)
            ),
            "No connected Android devices were available for verification.",
        )
        return VerificationResult("verification_failed", unavailable)

    requested_device = str(action.args.get("device_id", "")).strip()
    if requested_device:
        matched = any(str(item.get("device_id", "")).strip() == requested_device for item in available)
        if not matched:
            return VerificationResult(
                "not_verified",
                f"Launch reported success but device '{requested_device}' was not present during verification.",
            )

    return VerificationResult(
        "verified",
        launch_detail or "Launch reported success and at least one target device remained available.",
    )


VERIFICATION_REGISTRY: dict[str, Callable[[AgentAction, object], VerificationResult]] = {
    "pc.open_app": _verify_pc_open_app,
    "android.launch_app": _verify_android_launch_app,
}


def _get_audit_log_path() -> Path:
    configured_path = os.getenv("AI_LAN_ACTION_AUDIT_PATH")
    if configured_path:
        return Path(configured_path)
    return ROOT / "temp" / "action_audit.jsonl"


@sentinel
def validate_action_args(action: AgentAction) -> None:
    tool_spec = TOOL_REGISTRY.get(action.action)
    if tool_spec is None:
        raise ActionSchemaError(f"No tool registered for action '{action.action}'.")

    missing_args = [name for name in tool_spec.required_args if name not in action.args]
    if missing_args:
        names = ", ".join(missing_args)
        raise ActionSchemaError(f"Missing required args for '{action.action}': {names}.")

    allowed_args = set(tool_spec.required_args) | set(tool_spec.optional_args)
    unexpected_args = set(action.args) - allowed_args
    if unexpected_args:
        names = ", ".join(sorted(unexpected_args))
        raise ActionSchemaError(f"Unexpected args for '{action.action}': {names}.")


@sentinel
def append_action_audit_log(action: AgentAction, result: ActionExecutionResult) -> None:
    path = _get_audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": action.to_dict(),
        "result": result.to_dict(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _augment_observation_with_verification(
    observation: object,
    verification: VerificationResult,
) -> Any:
    if isinstance(observation, dict):
        enriched = dict(observation)
    else:
        enriched = {"result": observation}
    enriched["verification_status"] = verification.status
    enriched["verification_detail"] = verification.detail
    return enriched


@sentinel
def _run_post_action_verification(action: AgentAction, observation: object) -> object:
    verifier = VERIFICATION_REGISTRY.get(action.action)
    if verifier is None:
        return observation

    try:
        verification = verifier(action, observation)
    except Exception as exc:
        verification = VerificationResult(
            status="verification_failed",
            detail=f"Verification error: {exc}",
        )

    return _augment_observation_with_verification(observation, verification)


@sentinel
def dispatch_agent_action(
    payload: str | dict[str, object] | AgentAction,
    *,
    confirmed: bool = False,
    dry_run: bool = False,
    log_to_audit: bool = True,
) -> ActionExecutionResult:
    action = payload if isinstance(payload, AgentAction) else parse_agent_action(payload)

    policy = evaluate_action_policy(action)
    if not policy.allowed:
        result = ActionExecutionResult(
            status="rejected",
            action=action.action,
            observation=None,
            policy_reason=policy.reason,
        )
        if log_to_audit:
            append_action_audit_log(action, result)
        return result

    validate_action_args(action)

    if policy.requires_confirmation and not confirmed:
        result = ActionExecutionResult(
            status="confirmation_required",
            action=action.action,
            observation=None,
            policy_reason=policy.reason,
        )
        if log_to_audit:
            append_action_audit_log(action, result)
        return result

    if dry_run:
        result = ActionExecutionResult(
            status="dry_run",
            action=action.action,
            observation={
                "would_execute": True,
                "args": action.args,
                "confirmed": confirmed,
            },
            policy_reason=policy.reason,
        )
        if log_to_audit:
            append_action_audit_log(action, result)
        return result

    tool_spec = TOOL_REGISTRY[action.action]
    observation = tool_spec.handler(**action.args)
    observation = _run_post_action_verification(action, observation)
    result = ActionExecutionResult(
        status="executed",
        action=action.action,
        observation=observation,
        policy_reason=policy.reason,
    )
    if log_to_audit:
        append_action_audit_log(action, result)
    return result
