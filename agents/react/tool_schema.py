from __future__ import annotations

"""Model-facing tool schema helpers for the ReAct planner."""

from dataclasses import asdict, dataclass

from agents.react.tool_risk import get_tool_risk_profile
from router.dispatch_core import TOOL_REGISTRY
from safety.policy_engine import ALLOWED_ACTIONS, CONFIRMATION_REQUIRED_ACTIONS, DENIED_ACTIONS

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "web.search": "Search the web for current external information.",
    "web.browser_fetch": "Open a web page, fetch visible content, and optionally capture a screenshot.",
    "memory.search": "Search stored long-term memory for relevant prior notes or conversation summaries.",
    "context.build": "Build combined runtime context from stored memory and ingested corpus snippets.",
    "pc.type_text": "Type text into the currently focused desktop application.",
    "pc.open_app": "Open a desktop application by name.",
    "pc.read_clipboard": "Read the current clipboard contents.",
    "pc.execute_shell": "Execute an allowlisted shell command when policy and adapter settings allow it.",
    "pc.get_system_status": "Get a summary of local system status and resource information.",
    "pc.list_running_apps": "List currently running desktop applications.",
    "pc.list_workspace_files": "List files in a workspace-relative folder.",
    "pc.inspect_screen": "Capture screen text or visible OCR hints from the current display.",
    "pc.ocr_image": "Run OCR on an image file path.",
    "pc.ocr_screen": "Capture a screenshot and run OCR on it.",
    "android.list_devices": "List connected Android devices visible through ADB.",
    "android.launch_app": "Launch an Android app by package name.",
    "android.tap": "Send a tap gesture to an Android device.",
    "android.swipe": "Send a swipe gesture to an Android device.",
    "android.capture_screenshot": "Capture a screenshot from an Android device.",
    "android.scrcpy_mirror": "Start Android screen mirroring through scrcpy.",
}


@dataclass(frozen=True)
class ModelToolSchema:
    name: str
    description: str
    required_args: list[str]
    optional_args: list[str]
    confirmation_required: bool
    risk: str
    risk_tier: str
    policy_mode: str
    risk_reasons: list[str]
    allowed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _infer_risk(action_name: str) -> str:
    if action_name in DENIED_ACTIONS:
        return "blocked"
    if action_name in CONFIRMATION_REQUIRED_ACTIONS:
        return "medium"
    return "low"


def build_model_tool_schema(
    tool_names: list[str] | tuple[str, ...] | None = None,
) -> list[ModelToolSchema]:
    selected_names = sorted(tool_names or TOOL_REGISTRY)
    schemas: list[ModelToolSchema] = []
    for name in selected_names:
        spec = TOOL_REGISTRY.get(name)
        if spec is None:
            continue
        risk_profile = get_tool_risk_profile(name)
        schemas.append(
            ModelToolSchema(
                name=name,
                description=_TOOL_DESCRIPTIONS.get(name, f"Use tool '{name}'."),
                required_args=list(spec.required_args),
                optional_args=list(spec.optional_args),
                confirmation_required=name in CONFIRMATION_REQUIRED_ACTIONS,
                risk=_infer_risk(name),
                risk_tier=risk_profile.risk_tier,
                policy_mode=risk_profile.policy_mode,
                risk_reasons=risk_profile.risk_reasons,
                allowed=name in ALLOWED_ACTIONS and name not in DENIED_ACTIONS,
            )
        )
    return schemas


def format_model_tool_schema(
    tool_names: list[str] | tuple[str, ...] | None = None,
) -> str:
    schemas = build_model_tool_schema(tool_names)
    if not schemas:
        return "(none)"
    lines: list[str] = []
    for item in schemas:
        required = ", ".join(item.required_args) if item.required_args else "none"
        optional = ", ".join(item.optional_args) if item.optional_args else "none"
        confirmation = "yes" if item.confirmation_required else "no"
        allowed = "yes" if item.allowed else "no"
        lines.extend(
            [
                f"- {item.name}",
                f"  description: {item.description}",
                f"  required_args: {required}",
                f"  optional_args: {optional}",
                f"  confirmation_required: {confirmation}",
                f"  risk: {item.risk}",
                f"  risk_tier: {item.risk_tier}",
                f"  policy_mode: {item.policy_mode}",
                f"  risk_reasons: {', '.join(item.risk_reasons) if item.risk_reasons else 'none'}",
                f"  allowed: {allowed}",
            ]
        )
    return "\n".join(lines)


__all__ = ["ModelToolSchema", "build_model_tool_schema", "format_model_tool_schema"]
