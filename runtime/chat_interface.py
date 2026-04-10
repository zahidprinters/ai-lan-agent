from __future__ import annotations

import json
import os
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.react.agent import ReactAgent
from agents.react.controller import NeuralActionController
from memory.short_term.buffer import ShortTermBuffer
from runtime.context import build_runtime_context
from runtime.perception_loop import PerceptionLoop, PerceptionSnapshot
from tools.context_builder import get_default_merged_corpus_path
from tools.memory_store import get_memory_db_path, store_conversation_summary

CHAT_HELP_TEXT = """Commands:
  /help              Show this help text
    /control           Show command/control center help
  /actions           Show supported natural-language actions
    /policy ...        View or edit policy lists (allow/deny/confirm)
    /settings ...      View or edit config/settings.yaml keys
    /env ...           View or set runtime environment variables
  /json { ... }      Send a raw action payload JSON
  /confirm           Confirm the last pending high-risk action
  /reject            Reject and clear the last pending action
  /history           Show recent conversation history
  /save [path]       Save chat session to JSON (default: temp/chat_sessions/latest.json)
  /load [path]       Load chat session from JSON (default: temp/chat_sessions/latest.json)
  /last              Show the last raw router result
  /quit              Exit chat

Natural examples:
  search ai lan roadmap
  list docs
  list files tests
  system status
  running apps
  clipboard
  memory typing confirmation
  open app notepad
  type hello from ai lan
  android devices
  context typing confirmation policy
"""


CONTROL_HELP_TEXT = """Control Center Commands:
    /control
    /policy show
    /policy add <allow|deny|confirm> <action>
    /policy remove <allow|deny|confirm> <action>
    /settings show
    /settings set <key> <value>
    /env show [prefix]
    /env set <NAME> <VALUE>
    /env unset <NAME>

Notes:
    - /policy edits config/policies.yaml and reloads policy runtime in-process.
    - /settings edits config/settings.yaml for persistent behavior defaults.
    - /env commands affect only this running chat process/session.
"""


ACTIONS_HELP_TEXT = """Supported natural-language actions:
  search <query>             -> web.search
  memory <query>             -> memory.search
  list docs                  -> pc.list_workspace_files (docs)
  list files [relative_path] -> pc.list_workspace_files
  clipboard                  -> pc.read_clipboard
  system status              -> pc.get_system_status
  running apps               -> pc.list_running_apps
  open app <name>            -> pc.open_app (confirmation required)
  type <text>                -> pc.type_text (confirmation required)
  android devices            -> android.list_devices
  context <query>            -> context.build
"""


DEFAULT_SESSION_PATH = Path("temp") / "chat_sessions" / "latest.json"
_SHORT_TERM_MAX_ITEMS = 40
_POLICY_GROUP_MAP = {
    "allow": "allow_actions",
    "deny": "deny_actions",
    "confirm": "require_confirmation",
}


def _resolve_policy_path() -> Path:
    configured = os.getenv("AI_LAN_POLICY_CONFIG_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("config") / "policies.yaml"


def _resolve_settings_path() -> Path:
    configured = os.getenv("AI_LAN_SETTINGS_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("config") / "settings.yaml"


def _parse_policy_lists(raw_text: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {
        "allow_actions": [],
        "deny_actions": [],
        "require_confirmation": [],
    }
    active: str | None = None
    for raw_line in raw_text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.endswith(":"):
            key = stripped[:-1].strip()
            active = key if key in parsed else None
            continue
        if stripped.startswith("- ") and active is not None:
            value = stripped[2:].strip()
            if value:
                parsed[active].append(value)
    return parsed


def _format_policy_lists(parsed: dict[str, list[str]]) -> str:
    lines = ["policy:"]
    for key in ("allow_actions", "deny_actions", "require_confirmation"):
        lines.append(f"  {key}:")
        for action in sorted(set(parsed.get(key, []))):
            lines.append(f"    - {action}")
    return "\n".join(lines) + "\n"


def _read_policy_lists(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {"allow_actions": [], "deny_actions": [], "require_confirmation": []}
    return _parse_policy_lists(path.read_text(encoding="utf-8"))


def _write_policy_lists(path: Path, parsed: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_format_policy_lists(parsed), encoding="utf-8")


def _coerce_scalar(value: str) -> object:
    normalized = value.strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"1", "0"}:
        return lowered == "1"
    try:
        if any(char in normalized for char in {".", "e", "E"}):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized.strip('"').strip("'")


def _read_settings_values(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    values: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        values[key.strip()] = _coerce_scalar(raw_value)
    return values


def _format_setting_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{str(value)}"'


def _write_settings_values(path: Path, values: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}: {_format_setting_value(values[key])}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reload_policy_runtime() -> None:
    import safety.policy_engine as policy_engine

    importlib.reload(policy_engine)


def _make_payload(
    *, thought: str, action: str, args: dict[str, object], safety_level: str
) -> dict[str, object]:
    return {
        "thought": thought,
        "action": action,
        "args": args,
        "safety_level": safety_level,
    }


def _json_text(payload: object) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _should_store_message(text: str) -> bool:
    return not text.startswith("/") or text.startswith("/json ")


def _close_session(session: object) -> None:
    closer = getattr(session, "close", None)
    if callable(closer):
        closer()


def _get_neural_max_steps() -> int:
    raw_value = os.getenv("AI_LAN_REACT_MAX_STEPS", "3").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return 3
    return min(max(parsed, 1), 5)


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, parsed)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_natural_action(message: str) -> dict[str, object] | None:
    text = message.strip()
    lowered = text.lower()

    if lowered.startswith("search ") and len(text.split(maxsplit=1)) == 2:
        query = text.split(maxsplit=1)[1].strip()
        if query:
            return _make_payload(
                thought=f"Search web for: {query}",
                action="web.search",
                args={"query": query},
                safety_level="low",
            )

    if lowered.startswith("web ") and len(text.split(maxsplit=1)) == 2:
        query = text.split(maxsplit=1)[1].strip()
        if query:
            return _make_payload(
                thought=f"Search web for: {query}",
                action="web.search",
                args={"query": query},
                safety_level="low",
            )

    if lowered.startswith("memory ") and len(text.split(maxsplit=1)) == 2:
        query = text.split(maxsplit=1)[1].strip()
        if query:
            return _make_payload(
                thought=f"Search memory for: {query}",
                action="memory.search",
                args={"query": query},
                safety_level="low",
            )

    if lowered.startswith("context ") and len(text.split(maxsplit=1)) == 2:
        query = text.split(maxsplit=1)[1].strip()
        if query:
            return _make_payload(
                thought=f"Build context for: {query}",
                action="context.build",
                args={"query": query, "memory_limit": 5, "snippet_limit": 5},
                safety_level="low",
            )

    if lowered == "list docs":
        return _make_payload(
            thought="List docs folder files",
            action="pc.list_workspace_files",
            args={"relative_path": "docs", "limit": 20},
            safety_level="low",
        )

    if lowered.startswith("list files"):
        relative_path = "."
        parts = text.split(maxsplit=2)
        if len(parts) == 3:
            relative_path = parts[2].strip() or "."
        return _make_payload(
            thought=f"List workspace files at {relative_path}",
            action="pc.list_workspace_files",
            args={"relative_path": relative_path, "limit": 20},
            safety_level="low",
        )

    if lowered in {"clipboard", "read clipboard"}:
        return _make_payload(
            thought="Read clipboard",
            action="pc.read_clipboard",
            args={},
            safety_level="low",
        )

    if lowered in {"system status", "status"}:
        return _make_payload(
            thought="Get system status",
            action="pc.get_system_status",
            args={},
            safety_level="low",
        )

    if lowered in {"running apps", "apps"}:
        return _make_payload(
            thought="List running apps",
            action="pc.list_running_apps",
            args={"limit": 10},
            safety_level="low",
        )

    if lowered.startswith("open app ") and len(text.split(maxsplit=2)) == 3:
        app_name = text.split(maxsplit=2)[2].strip()
        if app_name:
            return _make_payload(
                thought=f"Open app {app_name}",
                action="pc.open_app",
                args={"app_name": app_name},
                safety_level="medium",
            )

    if lowered.startswith("type ") and len(text.split(maxsplit=1)) == 2:
        typed_text = text.split(maxsplit=1)[1].strip()
        if typed_text:
            return _make_payload(
                thought="Type provided text",
                action="pc.type_text",
                args={"text": typed_text},
                safety_level="medium",
            )

    if lowered in {"android devices", "list android devices"}:
        return _make_payload(
            thought="List Android devices",
            action="android.list_devices",
            args={},
            safety_level="low",
        )

    return None


def fallback_reply(message: str) -> str:
    lowered = message.strip().lower()
    if lowered in {"hi", "hello", "hey", "salam", "assalamualaikum"}:
        return "Hello. I am ready. Try '/help' or '/actions' to see what I can do."
    if "how are you" in lowered:
        return "I am operational and ready to execute safe tool actions."
    if "what can you do" in lowered or lowered == "help":
        return "I can run routed actions like web search, memory lookup, file listing, and system status. Use '/actions'."
    return (
        "I can run tool actions in chat mode. Try commands like 'search <query>', "
        "'context <query>', 'list docs', 'system status', or '/actions'."
    )


def format_router_result(result: dict[str, Any]) -> str:
    status = str(result.get("status", "unknown"))
    action = str(result.get("action", "(none)"))
    reason = str(result.get("policy_reason", ""))
    observation = result.get("observation")

    lines = [f"status: {status}", f"action: {action}"]
    if reason:
        lines.append(f"policy: {reason}")

    if observation is not None:
        if isinstance(observation, (dict, list)):
            lines.append("observation:")
            lines.append(json.dumps(observation, ensure_ascii=True, indent=2))
        else:
            lines.append(f"observation: {observation}")

    return "\n".join(lines)


@dataclass
class ChatSession:
    agent: ReactAgent = field(default_factory=ReactAgent)
    controller: NeuralActionController = field(default_factory=NeuralActionController)
    pending_payload: dict[str, object] | None = None
    pending_user_text: str | None = None
    last_result: dict[str, Any] | None = None
    last_context: dict[str, Any] | None = None
    last_plan: dict[str, Any] | None = None
    turns: list[dict[str, str]] = field(default_factory=list)
    short_term_buffer: ShortTermBuffer = field(
        default_factory=lambda: ShortTermBuffer(max_items=_SHORT_TERM_MAX_ITEMS)
    )
    memory_db_path: Path = field(default_factory=get_memory_db_path)
    merged_corpus_path: Path = field(default_factory=get_default_merged_corpus_path)
    memory_backend: str = field(
        default_factory=lambda: os.getenv("AI_LAN_MEMORY_BACKEND", "none").strip().lower()
    )
    chroma_path: Path = field(
        default_factory=lambda: Path(os.getenv("AI_LAN_CHROMA_PATH", "temp/chroma"))
    )
    perception_enabled: bool = field(
        default_factory=lambda: os.getenv("AI_LAN_PERCEPTION_ENABLED", "0") == "1"
    )
    perception_interval_sec: int = field(
        default_factory=lambda: _env_int("AI_LAN_PERCEPTION_INTERVAL_SEC", 10)
    )
    perception_max_interval_sec: int = field(
        default_factory=lambda: _env_int("AI_LAN_PERCEPTION_MAX_INTERVAL_SEC", 30)
    )
    perception_adaptive: bool = field(
        default_factory=lambda: _env_bool("AI_LAN_PERCEPTION_ADAPTIVE", True)
    )
    runtime_context_max_chars: int = field(
        default_factory=lambda: _env_int("AI_LAN_RUNTIME_CONTEXT_MAX_CHARS", 4000, minimum=256)
    )
    perception_snapshot: PerceptionSnapshot | None = None
    perception_loop: PerceptionLoop | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.perception_enabled:
            return
        try:
            self.perception_loop = PerceptionLoop(
                interval_sec=self.perception_interval_sec,
                max_interval_sec=self.perception_max_interval_sec,
                adaptive=self.perception_adaptive,
                on_snapshot=self._handle_perception_snapshot,
            )
        except TypeError:
            # Compatibility path for lightweight test doubles and legacy loop constructors.
            self.perception_loop = PerceptionLoop(
                interval_sec=self.perception_interval_sec,
                on_snapshot=self._handle_perception_snapshot,
            )
        self.perception_loop.start()

    def _append_turn(self, role: str, message: str) -> None:
        normalized_message = message.strip()
        if not normalized_message:
            return
        self.turns.append({"role": role, "message": normalized_message})
        self.short_term_buffer.add(message=normalized_message, role=role)

    def _handle_perception_snapshot(self, snapshot: PerceptionSnapshot) -> None:
        self.perception_snapshot = snapshot

    def close(self) -> None:
        if self.perception_loop is not None:
            self.perception_loop.stop()
            self.perception_loop = None

    def _run_payload(
        self, payload: dict[str, object], *, confirmed: bool = False
    ) -> dict[str, Any]:
        policy_context = self.last_context if isinstance(self.last_context, dict) else None
        return self.agent.run_step(
            payload,
            confirmed=confirmed,
            policy_context=policy_context,
        ).result

    def _resolve_session_path(self, raw_path: str | None = None) -> Path:
        if raw_path is None or not raw_path.strip():
            return DEFAULT_SESSION_PATH
        return Path(raw_path.strip())

    def _context_query_for_message(self, text: str) -> str:
        if text in {"/confirm", "/reject"} and self.pending_user_text:
            return self.pending_user_text
        return text

    def _build_context(self, text: str) -> dict[str, Any]:
        query = self._context_query_for_message(text)
        try:
            return build_runtime_context(
                query=query,
                short_term_buffer=self.short_term_buffer,
                memory_db_path=self.memory_db_path,
                memory_backend=self.memory_backend,
                chroma_path=self.chroma_path,
                perception_summary=(self.perception_snapshot.summary if self.perception_snapshot else None),
                max_context_chars=self.runtime_context_max_chars,
                merged_corpus_path=self.merged_corpus_path,
            )
        except Exception as exc:
            return {"query": query, "error": str(exc)}

    def _run_neural_controller(self, text: str) -> str | None:
        action_results: list[tuple[dict[str, object], dict[str, Any]]] = []

        def observe_action(payload: dict[str, object]) -> str:
            result = self._run_payload(payload, confirmed=False)
            self.last_result = result
            action_results.append((payload, result))
            return format_router_result(result)

        turns = self.controller.plan_iterative(
            message=text,
            max_steps=_get_neural_max_steps(),
            runtime_context=self.last_context,
            recent_turns=self.turns[-8:],
            recent_thoughts=self.agent.state.thoughts[-8:],
            recent_observations=self.agent.state.observations[-8:],
            observe_action=observe_action,
        )
        if not turns:
            return None

        final_turn = turns[-1]
        if final_turn.mode == "reply" and final_turn.reply_text:
            self._store_plan(
                source=final_turn.source,
                mode="reply",
                reply_text=final_turn.reply_text,
                raw_text=final_turn.raw_text,
                metadata=final_turn.metadata,
            )
            self._append_turn("assistant", final_turn.reply_text)
            result_payload: dict[str, Any] = {
                "status": "chat",
                "action": str(action_results[-1][1].get("action", "none")) if action_results else "none",
                "source": final_turn.source,
                "step_count": len(turns),
            }
            self._record_summary(text, final_turn.reply_text, result=result_payload, plan=self.last_plan)
            return final_turn.reply_text

        if action_results:
            payload, result = action_results[-1]
            self._store_plan(
                source=final_turn.source,
                mode="action",
                action=str(payload.get("action", "")),
                raw_text=final_turn.raw_text,
                metadata=final_turn.metadata,
            )
            if result.get("status") == "confirmation_required":
                self.pending_payload = payload
                self.pending_user_text = text
                rendered = (
                    f"{format_router_result(result)}\n"
                    "This action needs confirmation. Use /confirm to execute or /reject to cancel."
                )
                self._append_turn("assistant", rendered)
                return rendered

            self.pending_payload = None
            self.pending_user_text = None
            rendered = format_router_result(result)
            self._append_turn("assistant", rendered)
            self._record_summary(text, rendered, result=result, plan=self.last_plan)
            return rendered

        return None

    def _store_plan(
        self,
        *,
        source: str,
        mode: str,
        action: str | None = None,
        reply_text: str | None = None,
        raw_text: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        plan: dict[str, object] = {"source": source, "mode": mode}
        if action:
            plan["action"] = action
        if reply_text:
            plan["reply_text"] = reply_text
        if raw_text:
            plan["raw_text"] = raw_text
        if metadata:
            plan["metadata"] = dict(metadata)
        self.last_plan = plan
        return plan

    def _storage_source_text(self, text: str) -> str | None:
        candidate = (
            self.pending_user_text if text == "/confirm" and self.pending_user_text else text
        )
        if not _should_store_message(candidate):
            return None
        return candidate

    def _record_summary(
        self,
        user_text: str,
        assistant_text: str,
        *,
        result: dict[str, Any] | None = None,
        confirmed: bool = False,
        source_text: str | None = None,
        plan: dict[str, object] | None = None,
    ) -> None:
        storage_text = (
            source_text if source_text is not None else self._storage_source_text(user_text)
        )
        if storage_text is None:
            return

        metadata: dict[str, object] = {
            "source": "chat_session",
            "confirmed": confirmed,
        }
        if result is None:
            metadata.update({"status": "chat", "action": "none"})
        else:
            metadata.update(
                {
                    "status": str(result.get("status", "")),
                    "action": str(result.get("action", "")),
                }
            )
        if plan is not None:
            metadata["planner_source"] = str(plan.get("source", ""))
            metadata["planner_mode"] = str(plan.get("mode", ""))
            if plan.get("action"):
                metadata["planner_action"] = str(plan.get("action", ""))

        try:
            store_conversation_summary(
                user_text=storage_text,
                assistant_text=assistant_text,
                metadata=metadata,
                db_path=self.memory_db_path,
                memory_backend=self.memory_backend,
                chroma_path=self.chroma_path,
            )
        except Exception:
            return

    def _reset_short_term_buffer(self) -> None:
        self.short_term_buffer = ShortTermBuffer(max_items=_SHORT_TERM_MAX_ITEMS)
        for turn in self.turns:
            self.short_term_buffer.add(message=turn["message"], role=turn["role"])

    def save_session(self, raw_path: str | None = None) -> Path:
        target = self._resolve_session_path(raw_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "turns": self.turns,
            "pending_payload": self.pending_payload,
            "pending_user_text": self.pending_user_text,
            "last_result": self.last_result,
            "last_context": self.last_context,
            "last_plan": self.last_plan,
            "memory_db_path": str(self.memory_db_path),
            "merged_corpus_path": str(self.merged_corpus_path),
            "memory_backend": self.memory_backend,
            "chroma_path": str(self.chroma_path),
            "perception_enabled": self.perception_enabled,
            "perception_interval_sec": self.perception_interval_sec,
            "perception_max_interval_sec": self.perception_max_interval_sec,
            "perception_adaptive": self.perception_adaptive,
            "runtime_context_max_chars": self.runtime_context_max_chars,
            "perception_snapshot": (
                self.perception_snapshot.to_dict() if self.perception_snapshot is not None else None
            ),
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, default=str), encoding="utf-8"
        )
        return target

    def load_session(self, raw_path: str | None = None) -> Path:
        target = self._resolve_session_path(raw_path)
        if not target.exists():
            raise FileNotFoundError(f"Session file not found: {target}")

        payload_obj = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload_obj, dict):
            raise ValueError("Session payload must be a JSON object.")

        turns_obj = payload_obj.get("turns", [])
        if not isinstance(turns_obj, list):
            raise ValueError("Session field 'turns' must be a list.")
        parsed_turns: list[dict[str, str]] = []
        for item in turns_obj:
            if isinstance(item, dict):
                role = str(item.get("role", "unknown"))
                message = str(item.get("message", ""))
                if message.strip():
                    parsed_turns.append({"role": role, "message": message.strip()})

        pending_obj = payload_obj.get("pending_payload")
        if pending_obj is not None and not isinstance(pending_obj, dict):
            raise ValueError("Session field 'pending_payload' must be an object or null.")

        pending_user_text_obj = payload_obj.get("pending_user_text")
        if pending_user_text_obj is not None and not isinstance(pending_user_text_obj, str):
            raise ValueError("Session field 'pending_user_text' must be a string or null.")

        result_obj = payload_obj.get("last_result")
        if result_obj is not None and not isinstance(result_obj, dict):
            raise ValueError("Session field 'last_result' must be an object or null.")

        last_context_obj = payload_obj.get("last_context")
        if last_context_obj is not None and not isinstance(last_context_obj, dict):
            raise ValueError("Session field 'last_context' must be an object or null.")

        last_plan_obj = payload_obj.get("last_plan")
        if last_plan_obj is not None and not isinstance(last_plan_obj, dict):
            raise ValueError("Session field 'last_plan' must be an object or null.")

        memory_db_obj = payload_obj.get("memory_db_path")
        merged_corpus_obj = payload_obj.get("merged_corpus_path")
        memory_backend_obj = payload_obj.get("memory_backend")
        chroma_path_obj = payload_obj.get("chroma_path")
        perception_enabled_obj = payload_obj.get("perception_enabled")
        perception_interval_obj = payload_obj.get("perception_interval_sec")
        perception_max_interval_obj = payload_obj.get("perception_max_interval_sec")
        perception_adaptive_obj = payload_obj.get("perception_adaptive")
        runtime_context_max_chars_obj = payload_obj.get("runtime_context_max_chars")
        perception_snapshot_obj = payload_obj.get("perception_snapshot")

        self.turns = parsed_turns
        self.pending_payload = pending_obj if isinstance(pending_obj, dict) else None
        self.pending_user_text = (
            pending_user_text_obj.strip() if isinstance(pending_user_text_obj, str) else None
        )
        self.last_result = result_obj if isinstance(result_obj, dict) else None
        self.last_context = last_context_obj if isinstance(last_context_obj, dict) else None
        self.last_plan = last_plan_obj if isinstance(last_plan_obj, dict) else None
        if isinstance(memory_db_obj, str) and memory_db_obj.strip():
            self.memory_db_path = Path(memory_db_obj)
        if isinstance(merged_corpus_obj, str) and merged_corpus_obj.strip():
            self.merged_corpus_path = Path(merged_corpus_obj)
        if isinstance(memory_backend_obj, str) and memory_backend_obj.strip():
            self.memory_backend = memory_backend_obj.strip().lower()
        if isinstance(chroma_path_obj, str) and chroma_path_obj.strip():
            self.chroma_path = Path(chroma_path_obj)
        if isinstance(perception_enabled_obj, bool):
            self.perception_enabled = perception_enabled_obj
        if isinstance(perception_interval_obj, int):
            self.perception_interval_sec = perception_interval_obj
        if isinstance(perception_max_interval_obj, int):
            self.perception_max_interval_sec = perception_max_interval_obj
        if isinstance(perception_adaptive_obj, bool):
            self.perception_adaptive = perception_adaptive_obj
        if isinstance(runtime_context_max_chars_obj, int):
            self.runtime_context_max_chars = runtime_context_max_chars_obj
        if isinstance(perception_snapshot_obj, dict):
            timestamp = str(perception_snapshot_obj.get("timestamp", "")).strip()
            summary = str(perception_snapshot_obj.get("summary", "")).strip()
            source = str(perception_snapshot_obj.get("source", "screen_ocr")).strip() or "screen_ocr"
            if timestamp and summary:
                self.perception_snapshot = PerceptionSnapshot(
                    timestamp=timestamp,
                    summary=summary,
                    source=source,
                )
        self._reset_short_term_buffer()
        return target

    def format_history(self, limit: int = 20) -> str:
        if not self.turns:
            return "No conversation history yet."
        recent_turns = self.turns[-max(limit, 1) :]
        lines = [f"{item['role']}: {item['message']}" for item in recent_turns]
        return "\n".join(lines)

    def get_state(self, limit: int = 20) -> dict[str, Any]:
        recent_turns = self.turns[-max(limit, 1) :]
        return {
            "turn_count": len(self.turns),
            "pending_confirmation": self.pending_payload is not None,
            "pending_payload": self.pending_payload,
            "pending_payload_json": _json_text(self.pending_payload),
            "pending_user_text": self.pending_user_text,
            "last_result": self.last_result,
            "last_result_json": _json_text(self.last_result),
            "last_context": self.last_context,
            "last_context_json": _json_text(self.last_context),
            "last_plan": self.last_plan,
            "last_plan_json": _json_text(self.last_plan),
            "turns": recent_turns,
            "short_term_context": self.short_term_buffer.to_context_text(limit=limit),
            "memory_db_path": str(self.memory_db_path),
            "memory_backend": self.memory_backend,
            "chroma_path": str(self.chroma_path),
            "perception_enabled": self.perception_enabled,
            "perception_interval_sec": self.perception_interval_sec,
            "perception_max_interval_sec": self.perception_max_interval_sec,
            "perception_adaptive": self.perception_adaptive,
            "runtime_context_max_chars": self.runtime_context_max_chars,
            "perception_snapshot": (
                self.perception_snapshot.to_dict() if self.perception_snapshot is not None else None
            ),
            "merged_corpus_path": str(self.merged_corpus_path),
        }

    def handle_message(self, message: str) -> str:
        text = message.strip()
        if not text:
            return "Please type a message. Use /help for commands."

        self._append_turn("user", text)
        self.last_context = self._build_context(text)

        if text == "/help":
            self._append_turn("assistant", CHAT_HELP_TEXT)
            return CHAT_HELP_TEXT
        if text == "/control":
            self._append_turn("assistant", CONTROL_HELP_TEXT)
            return CONTROL_HELP_TEXT
        if text.startswith("/policy"):
            reply = self._handle_policy_command(text)
            self._append_turn("assistant", reply)
            return reply
        if text.startswith("/settings"):
            reply = self._handle_settings_command(text)
            self._append_turn("assistant", reply)
            return reply
        if text.startswith("/env"):
            reply = self._handle_env_command(text)
            self._append_turn("assistant", reply)
            return reply
        if text == "/actions":
            self._append_turn("assistant", ACTIONS_HELP_TEXT)
            return ACTIONS_HELP_TEXT
        if text.startswith("/history"):
            history = self.format_history()
            self._append_turn("assistant", history)
            return history
        if text == "/last":
            if self.last_result is None:
                reply = "No previous result yet."
                self._append_turn("assistant", reply)
                return reply
            serialized = _json_text(self.last_result)
            self._append_turn("assistant", serialized)
            return serialized
        if text == "/reject":
            if self.pending_payload is None:
                reply = "No pending action to reject."
                self._append_turn("assistant", reply)
                return reply
            self.pending_payload = None
            self.pending_user_text = None
            reply = "Pending action rejected."
            self._append_turn("assistant", reply)
            return reply
        if text.startswith("/save"):
            path_arg = text[len("/save") :].strip()
            target = self.save_session(path_arg if path_arg else None)
            reply = f"Session saved: {target}"
            self._append_turn("assistant", reply)
            return reply
        if text.startswith("/load"):
            path_arg = text[len("/load") :].strip()
            try:
                target = self.load_session(path_arg if path_arg else None)
            except Exception as exc:
                reply = f"Failed to load session: {exc}"
                self._append_turn("assistant", reply)
                return reply
            reply = f"Session loaded: {target}"
            self._append_turn("assistant", reply)
            return reply
        if text == "/confirm":
            if self.pending_payload is None:
                reply = "No pending action."
                self._append_turn("assistant", reply)
                return reply

            source_text = self.pending_user_text or text
            try:
                result = self._run_payload(self.pending_payload, confirmed=True)
            except Exception as exc:
                error_text = f"Execution error: {exc}"
                self._append_turn("assistant", error_text)
                return error_text

            self.last_result = result
            rendered = format_router_result(result)
            self.pending_payload = None
            self.pending_user_text = None
            self._append_turn("assistant", rendered)
            self._record_summary(
                text,
                rendered,
                result=result,
                confirmed=True,
                source_text=source_text,
                plan=self.last_plan,
            )
            return rendered

        payload: dict[str, object] | None = None
        if text.startswith("/json "):
            raw = text[6:].strip()
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError as exc:
                reply = f"Invalid JSON: {exc.msg}"
                self._append_turn("assistant", reply)
                return reply
            if not isinstance(loaded, dict):
                reply = "JSON payload must be an object."
                self._append_turn("assistant", reply)
                return reply
            payload = {str(key): value for key, value in loaded.items()}
            self._store_plan(
                source="json",
                mode="action",
                action=str(payload.get("action", "")),
            )
        else:
            payload = parse_natural_action(text)
            if payload is not None:
                self._store_plan(
                    source="deterministic",
                    mode="action",
                    action=str(payload.get("action", "")),
                )
            else:
                neural_reply = self._run_neural_controller(text)
                if neural_reply is not None:
                    return neural_reply

        if payload is None:
            fallback = fallback_reply(text)
            self._store_plan(source="fallback", mode="reply", reply_text=fallback)
            self._append_turn("assistant", fallback)
            self._record_summary(text, fallback, plan=self.last_plan)
            return fallback

        try:
            result = self._run_payload(payload, confirmed=False)
        except Exception as exc:
            error_text = f"Execution error: {exc}"
            self._append_turn("assistant", error_text)
            self._record_summary(
                text,
                error_text,
                result={"status": "error", "action": str(payload.get("action", ""))},
                plan=self.last_plan,
            )
            return error_text

        self.last_result = result
        if result.get("status") == "confirmation_required":
            self.pending_payload = payload
            self.pending_user_text = text
            rendered = (
                f"{format_router_result(result)}\n"
                "This action needs confirmation. Use /confirm to execute or /reject to cancel."
            )
            self._append_turn("assistant", rendered)
            return rendered

        self.pending_payload = None
        self.pending_user_text = None
        rendered = format_router_result(result)
        self._append_turn("assistant", rendered)
        self._record_summary(text, rendered, result=result, plan=self.last_plan)
        return rendered

    def _handle_policy_command(self, text: str) -> str:
        parts = text.split(maxsplit=3)
        if len(parts) == 1 or (len(parts) == 2 and parts[1] == "show"):
            path = _resolve_policy_path()
            parsed = _read_policy_lists(path)
            return json.dumps(
                {
                    "policy_path": str(path),
                    "allow_actions": sorted(parsed.get("allow_actions", [])),
                    "deny_actions": sorted(parsed.get("deny_actions", [])),
                    "require_confirmation": sorted(parsed.get("require_confirmation", [])),
                },
                ensure_ascii=True,
                indent=2,
            )

        if len(parts) < 4:
            return "Usage: /policy add|remove <allow|deny|confirm> <action>"

        operation = parts[1].strip().lower()
        group_alias = parts[2].strip().lower()
        action_name = parts[3].strip().lower()
        if operation not in {"add", "remove"}:
            return "Policy operation must be add or remove."
        group = _POLICY_GROUP_MAP.get(group_alias)
        if group is None:
            return "Policy group must be one of: allow, deny, confirm."
        if not action_name:
            return "Action name cannot be empty."

        path = _resolve_policy_path()
        parsed = _read_policy_lists(path)
        existing = set(parsed.get(group, []))
        if operation == "add":
            existing.add(action_name)
        else:
            existing.discard(action_name)
        parsed[group] = sorted(existing)
        _write_policy_lists(path, parsed)
        _reload_policy_runtime()

        return (
            f"Policy updated at {path}: {operation} {action_name} in {group}. "
            "Changes apply to new router policy checks in this session."
        )

    def _handle_settings_command(self, text: str) -> str:
        parts = text.split(maxsplit=3)
        path = _resolve_settings_path()
        values = _read_settings_values(path)

        if len(parts) == 1 or (len(parts) == 2 and parts[1] == "show"):
            return json.dumps(
                {
                    "settings_path": str(path),
                    "values": values,
                },
                ensure_ascii=True,
                indent=2,
                default=str,
            )

        if len(parts) < 4 or parts[1].strip().lower() != "set":
            return "Usage: /settings show OR /settings set <key> <value>"

        key = parts[2].strip()
        raw_value = parts[3].strip()
        if not key:
            return "Settings key cannot be empty."

        values[key] = _coerce_scalar(raw_value)
        _write_settings_values(path, values)
        return f"Settings updated at {path}: {key}={values[key]!r}"

    def _handle_env_command(self, text: str) -> str:
        parts = text.split(maxsplit=3)
        if len(parts) == 1 or (len(parts) == 2 and parts[1].strip().lower() == "show"):
            prefix = "AI_LAN_"
            env_view = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
            return json.dumps(
                {
                    "scope": "current_process",
                    "filter_prefix": prefix,
                    "values": dict(sorted(env_view.items())),
                },
                ensure_ascii=True,
                indent=2,
            )

        command = parts[1].strip().lower() if len(parts) >= 2 else ""
        if command == "show":
            prefix = parts[2].strip() if len(parts) >= 3 else "AI_LAN_"
            env_view = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
            return json.dumps(
                {
                    "scope": "current_process",
                    "filter_prefix": prefix,
                    "values": dict(sorted(env_view.items())),
                },
                ensure_ascii=True,
                indent=2,
            )

        if command == "set":
            if len(parts) < 4:
                return "Usage: /env set <NAME> <VALUE>"
            name = parts[2].strip()
            value = parts[3]
            if not name:
                return "Environment variable name cannot be empty."
            os.environ[name] = value
            return (
                f"Environment updated for current session: {name}={value}. "
                "Use /settings set for persistent project defaults."
            )

        if command == "unset":
            if len(parts) < 3:
                return "Usage: /env unset <NAME>"
            name = parts[2].strip()
            if not name:
                return "Environment variable name cannot be empty."
            os.environ.pop(name, None)
            return f"Environment variable cleared for current session: {name}"

        return "Usage: /env show [prefix] OR /env set <NAME> <VALUE> OR /env unset <NAME>"


def run_chat_cli() -> int:
    session = ChatSession()
    print("AI Lan Chat Interface (CLI)")
    print("Type /help for commands. Type /quit to exit.")

    try:
        while True:
            try:
                user_input = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting chat.")
                return 0

            if user_input in {"/quit", "/exit"}:
                print("Exiting chat.")
                return 0

            reply = session.handle_message(user_input)
            print("ai> " + reply.replace("\n", "\nai> "))
    finally:
        _close_session(session)


__all__ = [
    "ACTIONS_HELP_TEXT",
    "CHAT_HELP_TEXT",
    "ChatSession",
    "DEFAULT_SESSION_PATH",
    "fallback_reply",
    "format_router_result",
    "parse_natural_action",
    "run_chat_cli",
]
