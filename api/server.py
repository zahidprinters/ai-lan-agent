from __future__ import annotations

import json
import os
import sys
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from runtime.dashboard_http import DashboardHttpConfig, DashboardRouteSet, build_dashboard_handler
from runtime.chat_interface import ChatSession
from runtime.context import build_runtime_context
from training.checkpoints import build_sorted_summaries
from training.config import ProjectConfig, load_config
from training.model_registry import get_active_model, init_registry, list_registered_models
from tools.memory_store import get_recent_memories, retrieve_relevant_memories

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTION_AUDIT_PATH = ROOT / "temp" / "action_audit.jsonl"
DEFAULT_ERROR_LOG_PATH = ROOT / "logs" / "errors.log"
DEFAULT_LEGACY_ACTION_LOG_PATH = ROOT / "logs" / "actions.log"


def _resolve_action_audit_path() -> Path:
    configured = os.getenv("AI_LAN_ACTION_AUDIT_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_ACTION_AUDIT_PATH


def _tail_text(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line.strip()]
    return lines[-max(limit, 1) :]


def _tail_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line in _tail_text(path, limit):
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            entries.append({"raw": line})
        else:
            entries.append(loaded if isinstance(loaded, dict) else {"raw": loaded})
    return entries


def _resolve_query(session: ChatSession, query: str | None) -> str:
    if query and query.strip():
        return query.strip()
    if session.last_context and isinstance(session.last_context.get("query"), str):
        last_query = str(session.last_context.get("query", "")).strip()
        if last_query:
            return last_query
    for turn in reversed(session.turns):
        if turn.get("role") == "user" and turn.get("message", "").strip():
            return str(turn["message"]).strip()
    return ""


def _model_registry_path(config: ProjectConfig) -> Path:
    return config.runs_dir / "model_registry.json"


def _serialize_active_model(active: dict[str, Any] | None) -> dict[str, Any]:
    if active is None:
        return {"active_version": None, "record": None}
    return {"active_version": active.get("version"), "record": active}


@dataclass
class DashboardApp:
    session: ChatSession
    config: ProjectConfig
    registry_path: Path


def create_app(
    *, session: ChatSession | None = None, config: ProjectConfig | None = None
) -> DashboardApp:
    resolved_config = config or load_config()
    resolved_session = session or ChatSession()
    return DashboardApp(
        session=resolved_session,
        config=resolved_config,
        registry_path=_model_registry_path(resolved_config),
    )


def build_runs_payload(
    config: ProjectConfig, *, limit: int = 10, show_all: bool = False
) -> dict[str, Any]:
    summaries = build_sorted_summaries(config.runs_dir, config.data_path.resolve())
    project_summaries = [item for item in summaries if item.get("is_project_run")]
    visible_summaries = summaries if show_all or not project_summaries else project_summaries
    max_limit = max(limit, 1)

    return {
        "index_path": str(config.run_index_path),
        "all_index_path": str(config.run_all_index_path),
        "project_run_count": len(project_summaries),
        "all_run_count": len(summaries),
        "visible_run_count": len(visible_summaries),
        "project_runs": project_summaries[:max_limit],
        "visible_runs": visible_summaries[:max_limit],
        "all_runs": summaries[:max_limit],
        "best_run": visible_summaries[0] if visible_summaries else None,
    }


def build_models_payload(config: ProjectConfig) -> dict[str, Any]:
    registry_path = _model_registry_path(config)
    init_registry(registry_path)
    records = list_registered_models(registry_path)
    active = get_active_model(registry_path)
    return {
        "registry_path": str(registry_path),
        "record_count": len(records),
        "records": records,
        "active": _serialize_active_model(active),
    }


def build_memory_payload(
    session: ChatSession,
    *,
    query: str | None = None,
    limit: int = 10,
    kind: str | None = None,
) -> dict[str, Any]:
    resolved_query = _resolve_query(session, query)
    recent = get_recent_memories(limit=limit, kind=kind, db_path=session.memory_db_path)
    query_hits = (
        retrieve_relevant_memories(
            query=resolved_query,
            limit=limit,
            kind=kind,
            db_path=session.memory_db_path,
            memory_backend=session.memory_backend,
            chroma_path=session.chroma_path,
        )
        if resolved_query
        else []
    )
    return {
        "query": resolved_query,
        "kind": kind,
        "db_path": str(session.memory_db_path),
        "memory_backend": session.memory_backend,
        "chroma_path": str(session.chroma_path),
        "recent_count": len(recent),
        "query_hit_count": len(query_hits),
        "recent": [
            {
                "memory_id": entry.memory_id,
                "kind": entry.kind,
                "summary": entry.summary,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
            }
            for entry in recent
        ],
        "query_hits": [hit.to_dict() for hit in query_hits],
    }


def build_context_payload(
    session: ChatSession,
    *,
    query: str | None = None,
    memory_limit: int = 5,
    snippet_limit: int = 5,
) -> dict[str, Any]:
    resolved_query = _resolve_query(session, query)
    if (
        session.last_context
        and isinstance(session.last_context, dict)
        and str(session.last_context.get("query", "")).strip() == resolved_query
    ):
        return session.last_context

    context_payload = build_runtime_context(
        query=resolved_query,
        short_term_buffer=session.short_term_buffer,
        memory_limit=memory_limit,
        snippet_limit=snippet_limit,
        memory_db_path=session.memory_db_path,
        memory_backend=session.memory_backend,
        chroma_path=session.chroma_path,
        perception_summary=(session.perception_snapshot.summary if session.perception_snapshot else None),
        max_context_chars=session.runtime_context_max_chars,
        merged_corpus_path=session.merged_corpus_path,
    )
    session.last_context = context_payload
    return context_payload


def build_log_payload(*, limit: int = 25) -> dict[str, Any]:
    audit_path = _resolve_action_audit_path()
    return {
        "audit_path": str(audit_path),
        "audit_entries": _tail_jsonl(audit_path, limit),
        "error_path": str(DEFAULT_ERROR_LOG_PATH),
        "error_lines": _tail_text(DEFAULT_ERROR_LOG_PATH, limit),
        "legacy_action_path": str(DEFAULT_LEGACY_ACTION_LOG_PATH),
        "legacy_action_lines": _tail_text(DEFAULT_LEGACY_ACTION_LOG_PATH, limit),
    }


def build_ops_payload(app: DashboardApp) -> dict[str, Any]:
    registry_path = _model_registry_path(app.config)
    active_model = get_active_model(registry_path)
    best_model = app.config.best_model_path
    return {
        "registry_path": str(registry_path),
        "active_model": active_model,
        "commands": [
            {"label": "Train", "command": "python training/train_char_model.py"},
            {"label": "Generate", "command": "python training/generate.py"},
            {"label": "Evaluate", "command": f"python scripts/evaluate.py --model {best_model}"},
            {
                "label": "Export",
                "command": f"python scripts/export_model.py --model {best_model} --export deploy/weights.pt",
            },
            {
                "label": "Quantize",
                "command": f"python scripts/quantize_model.py --model {best_model}",
            },
            {"label": "Runs", "command": "python scripts/list_runs.py"},
            {"label": "Registry", "command": "python scripts/model_registry.py list --json"},
            {"label": "Memory", "command": "python scripts/memory_store.py recent"},
        ],
        "paths": {
            "model_path": str(app.config.model_path),
            "best_model_path": str(app.config.best_model_path),
            "tokenizer_path": str(app.config.tokenizer_path),
            "runs_dir": str(app.config.runs_dir),
            "run_index_path": str(app.config.run_index_path),
            "run_all_index_path": str(app.config.run_all_index_path),
            "memory_db_path": str(app.session.memory_db_path),
            "merged_corpus_path": str(app.session.merged_corpus_path),
            "perception_enabled": app.session.perception_enabled,
        },
        "perception": (
            app.session.perception_snapshot.to_dict()
            if app.session.perception_snapshot is not None
            else None
        ),
    }


def _build_cpu_pressure_payload() -> dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    if hasattr(os, "getloadavg"):
        try:
            load1, load5, load15 = os.getloadavg()
            load_ratio = float(load1) / max(cpu_count, 1)
            if load_ratio >= 1.0:
                band = "high"
            elif load_ratio >= 0.7:
                band = "elevated"
            else:
                band = "normal"
            return {
                "proxy_type": "loadavg",
                "cpu_count": cpu_count,
                "load_1m": round(float(load1), 4),
                "load_5m": round(float(load5), 4),
                "load_15m": round(float(load15), 4),
                "load_ratio_1m": round(load_ratio, 4),
                "thermal_proxy_band": band,
            }
        except (OSError, ValueError):
            pass
    return {
        "proxy_type": "unavailable",
        "cpu_count": cpu_count,
        "thermal_proxy_band": "unknown",
        "detail": "Load-average thermal proxy is not available on this platform.",
    }


def _build_memory_payload() -> dict[str, Any]:
    if sys.platform.startswith("win"):
        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        state = _MemoryStatus()
        state.dwLength = ctypes.sizeof(_MemoryStatus)
        success = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))
        if success:
            total = int(state.ullTotalPhys)
            available = int(state.ullAvailPhys)
            used = max(total - available, 0)
            usage_pct = (used / total * 100.0) if total else 0.0
            return {
                "platform": "windows",
                "total_bytes": total,
                "available_bytes": available,
                "used_bytes": used,
                "usage_percent": round(usage_pct, 2),
                "memory_load_percent": int(state.dwMemoryLoad),
            }

    return {
        "platform": sys.platform,
        "detail": "RAM telemetry is not available via standard runtime APIs on this platform.",
    }


def _build_model_confidence_payload(active_model: dict[str, Any] | None) -> dict[str, Any]:
    if not active_model:
        return {
            "status": "unavailable",
            "detail": "No active model is registered.",
            "confidence_score": None,
            "confidence_metric": None,
            "confidence_band": "unknown",
        }

    metrics_obj = active_model.get("metrics", {})
    metrics = metrics_obj if isinstance(metrics_obj, dict) else {}

    metric_name: str | None = None
    metric_value: float | None = None
    for candidate in ("quality_score", "accuracy", "confidence"):
        raw_value = metrics.get(candidate)
        if isinstance(raw_value, (int, float)):
            metric_name = candidate
            metric_value = float(raw_value)
            break

    if metric_value is None:
        return {
            "status": "partial",
            "detail": "Active model metrics do not include quality_score, accuracy, or confidence.",
            "confidence_score": None,
            "confidence_metric": None,
            "confidence_band": "unknown",
        }

    if metric_value >= 0.85:
        band = "high"
    elif metric_value >= 0.70:
        band = "medium"
    else:
        band = "low"

    return {
        "status": "ok",
        "detail": "Derived from active model metrics.",
        "confidence_score": round(metric_value, 4),
        "confidence_metric": metric_name,
        "confidence_band": band,
        "model_version": active_model.get("version"),
    }


def build_health_payload(app: DashboardApp) -> dict[str, Any]:
    registry_path = _model_registry_path(app.config)
    active_model = get_active_model(registry_path)
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": _build_cpu_pressure_payload(),
        "memory": _build_memory_payload(),
        "model_confidence": _build_model_confidence_payload(active_model),
    }


def build_dashboard_state(
    app: DashboardApp,
    *,
    query: str | None = None,
    runs_limit: int = 10,
    memory_limit: int = 10,
    snippet_limit: int = 5,
    log_limit: int = 25,
) -> dict[str, Any]:
    resolved_query = _resolve_query(app.session, query)
    return {
        "service": {
            "name": "AI Lan Dashboard",
            "version": app.config.version,
            "model_type": app.config.model_type,
        },
        "query": resolved_query,
        "session": app.session.get_state(limit=max(memory_limit, 20)),
        "context": build_context_payload(
            app.session,
            query=resolved_query,
            memory_limit=memory_limit,
            snippet_limit=snippet_limit,
        ),
        "memory": build_memory_payload(app.session, query=resolved_query, limit=memory_limit),
        "runs": build_runs_payload(app.config, limit=runs_limit),
        "models": build_models_payload(app.config),
        "logs": build_log_payload(limit=log_limit),
        "ops": build_ops_payload(app),
        "health": build_health_payload(app),
    }


def _build_chat_response(app: DashboardApp, message: str) -> dict[str, Any]:
    reply = app.session.handle_message(message)
    state = app.session.get_state()
    return {
        "reply": reply,
        "pending_confirmation": state["pending_confirmation"],
        "last_result_json": state["last_result_json"],
        "last_context_json": state["last_context_json"],
        "turn_count": state["turn_count"],
    }


def build_dashboard_routes(app: DashboardApp) -> DashboardRouteSet:
    return DashboardRouteSet(
        health=lambda: build_health_payload(app),
        session=lambda: app.session.get_state(),
        state=lambda query, runs_limit, memory_limit, snippet_limit, log_limit: build_dashboard_state(
            app,
            query=query,
            runs_limit=runs_limit,
            memory_limit=memory_limit,
            snippet_limit=snippet_limit,
            log_limit=log_limit,
        ),
        runs=lambda limit, show_all: build_runs_payload(app.config, limit=limit, show_all=show_all),
        models=lambda: build_models_payload(app.config),
        memory=lambda query, limit, kind: build_memory_payload(
            app.session,
            query=query,
            limit=limit,
            kind=kind,
        ),
        context=lambda query, memory_limit, snippet_limit: build_context_payload(
            app.session,
            query=query,
            memory_limit=memory_limit,
            snippet_limit=snippet_limit,
        ),
        logs=lambda limit: build_log_payload(limit=limit),
        ops=lambda: build_ops_payload(app),
        chat=lambda message: _build_chat_response(app, message),
    )


def build_handler(app: DashboardApp) -> type[BaseHTTPRequestHandler]:
    return build_dashboard_handler(
        build_dashboard_routes(app),
        config=DashboardHttpConfig(root_message="AI Lan dashboard API"),
    )


def run_api_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    app: DashboardApp | None = None,
) -> int:
    resolved_app = app or create_app()
    handler_class = build_handler(resolved_app)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"AI Lan Dashboard API listening at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard API server.")
    finally:
        server.server_close()
    return 0


__all__ = [
    "DashboardApp",
    "build_health_payload",
    "build_context_payload",
    "build_dashboard_state",
    "build_dashboard_routes",
    "build_handler",
    "build_log_payload",
    "build_memory_payload",
    "build_models_payload",
    "build_ops_payload",
    "build_runs_payload",
    "create_app",
    "run_api_server",
]
