from __future__ import annotations

import argparse
import json
from textwrap import shorten
from typing import Any

from _bootstrap import ensure_repo_root

ensure_repo_root()

from api.server import (
    build_context_payload,
    build_dashboard_state,
    build_log_payload,
    build_memory_payload,
    build_models_payload,
    build_ops_payload,
    create_app,
)
from runtime.chat_interface import ChatSession


def _section(title: str) -> None:
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


def _kv(label: str, value: object) -> None:
    text = "(none)" if value is None or value == "" else str(value)
    print(f"{label:<18} {text}")


def _truncate(value: object, width: int = 96) -> str:
    text = "(none)" if value is None else str(value).strip()
    return shorten(text, width=width, placeholder="...")


def _print_items(items: list[str], *, prefix: str = "-") -> None:
    if not items:
        print(f"{prefix} none")
        return
    for item in items:
        print(f"{prefix} {item}")


def _build_app() -> Any:
    return create_app(session=ChatSession())


def render_overview(
    app: Any,
    *,
    query: str | None,
    runs_limit: int,
    memory_limit: int,
    snippet_limit: int,
    log_limit: int,
) -> None:
    state = build_dashboard_state(
        app,
        query=query,
        runs_limit=runs_limit,
        memory_limit=memory_limit,
        snippet_limit=snippet_limit,
        log_limit=log_limit,
    )
    _section("Dashboard Overview")
    _kv("Service", state["service"]["name"])
    _kv("Version", state["service"]["version"])
    _kv("Model type", state["service"]["model_type"])
    _kv("Query", state["query"])
    _kv("Turn count", state["session"]["turn_count"])
    _kv("Pending", "yes" if state["session"]["pending_confirmation"] else "no")
    _kv("Runs", state["runs"]["visible_run_count"])
    _kv("Models", state["models"]["record_count"])
    _kv("Memory", state["memory"]["recent_count"])
    _kv("Logs", len(state["logs"]["audit_entries"]))

    print("")
    print("Latest run:")
    latest_run = state["runs"]["best_run"]
    if isinstance(latest_run, dict):
        print(f"- {latest_run.get('summary_file', '(unknown)')}")
        print(f"  model_type: {latest_run.get('model_type', 'char_mlp')}")
        print(f"  best_val_loss: {latest_run.get('best_val_loss', 'n/a')}")
    else:
        print("- none")

    print("")
    print("Recent memory:")
    _print_items(
        [
            f"[{entry['kind']}] {_truncate(entry['summary'])}"
            for entry in state["memory"]["recent"][:5]
        ]
    )

    print("")
    print("Recent logs:")
    _print_items([_truncate(line, 120) for line in state["logs"]["error_lines"][:5]])


def render_models(app: Any, *, limit: int) -> None:
    payload = build_models_payload(app.config)
    _section("Model Registry")
    _kv("Registry path", payload["registry_path"])
    _kv("Record count", payload["record_count"])

    active = payload.get("active") or {}
    _kv("Active version", active.get("active_version"))
    active_record = active.get("record")
    if isinstance(active_record, dict):
        _kv("Active model", active_record.get("model_path"))
        metrics = active_record.get("metrics") or {}
        if isinstance(metrics, dict) and metrics:
            print("Active metrics:")
            for key, value in metrics.items():
                print(f"- {key}: {value}")

    print("")
    print("Records:")
    records = payload.get("records", [])[: max(limit, 1)]
    if not records:
        print("- none")
        return

    for record in records:
        if not isinstance(record, dict):
            print(f"- {_truncate(record)}")
            continue
        bits: list[str] = [
            f"{record.get('version', '(unknown)')} -> {_truncate(record.get('model_path'))}"
        ]
        metrics = record.get("metrics") or {}
        if isinstance(metrics, dict) and metrics:
            metric_text = ", ".join(f"{key}={value}" for key, value in metrics.items())
            bits.append(metric_text)
        tags = record.get("tags") or []
        if isinstance(tags, list) and tags:
            bits.append("tags=" + ", ".join(str(tag) for tag in tags))
        notes = str(record.get("notes", "")).strip()
        if notes:
            bits.append(f"notes={_truncate(notes, 70)}")
        print(f"- {' | '.join(bits)}")


def render_memory(app: Any, *, query: str | None, limit: int, kind: str | None) -> None:
    payload = build_memory_payload(app.session, query=query, limit=limit, kind=kind)
    _section("Memory Store")
    _kv("DB path", payload["db_path"])
    _kv("Query", payload["query"] or "(recent)")
    _kv("Kind", payload["kind"])
    _kv("Recent count", payload["recent_count"])
    _kv("Query hits", payload["query_hit_count"])

    print("")
    print("Recent entries:")
    recent_entries = payload.get("recent", [])
    if not recent_entries:
        print("- none")
    for entry in recent_entries:
        print(f"- [{entry['kind']}] {entry['memory_id']}")
        print(f"  summary: {_truncate(entry['summary'])}")
        metadata = entry.get("metadata") or {}
        if isinstance(metadata, dict) and metadata:
            print(f"  metadata: {json.dumps(metadata, ensure_ascii=True, default=str)}")

    if query:
        print("")
        print("Query hits:")
        query_hits = payload.get("query_hits", [])
        if not query_hits:
            print("- none")
        for hit in query_hits[: max(limit, 1)]:
            if not isinstance(hit, dict):
                print(f"- {_truncate(hit)}")
                continue
            print(f"- [{hit.get('kind', '(unknown)')}] {hit.get('memory_id', '(unknown)')}")
            print(f"  score: {hit.get('score', 'n/a')}")
            print(f"  summary: {_truncate(hit.get('summary'))}")


def render_context(app: Any, *, query: str | None, memory_limit: int, snippet_limit: int) -> None:
    resolved_query = query.strip() if isinstance(query, str) and query.strip() else "system status"
    payload = build_context_payload(
        app.session,
        query=resolved_query,
        memory_limit=memory_limit,
        snippet_limit=snippet_limit,
    )
    retrieval = payload.get("retrieval") or {}
    _section("Context Assembly")
    _kv("Query", payload["query"])
    _kv(
        "Memory hits",
        len(retrieval.get("memory_hits", [])) if isinstance(retrieval, dict) else "n/a",
    )
    _kv(
        "Snippets",
        len(retrieval.get("corpus_snippets", [])) if isinstance(retrieval, dict) else "n/a",
    )

    print("")
    print("Short-term context:")
    print(payload.get("short_term_context") or "(none)")

    print("")
    print("Retrieved context:")
    print(str(retrieval.get("context_text", "")).strip() or "(none)")

    print("")
    print("Assembled context:")
    print(payload.get("assembled_context") or "(none)")


def render_logs(*, limit: int) -> None:
    payload = build_log_payload(limit=limit)
    _section("Logs")
    _kv("Audit path", payload["audit_path"])
    _kv("Error path", payload["error_path"])
    _kv("Legacy path", payload["legacy_action_path"])

    print("")
    print("Audit entries:")
    audit_entries = payload.get("audit_entries", [])
    if not audit_entries:
        print("- none")
    for entry in audit_entries[: max(limit, 1)]:
        print(f"- {json.dumps(entry, ensure_ascii=True, default=str)}")

    print("")
    print("Error lines:")
    _print_items(payload.get("error_lines", [])[: max(limit, 1)])

    print("")
    print("Legacy action lines:")
    _print_items(payload.get("legacy_action_lines", [])[: max(limit, 1)])


def render_ops(app: Any) -> None:
    payload = build_ops_payload(app)
    _section("System Control")
    _kv("Registry path", payload["registry_path"])
    active_model = payload.get("active_model")
    if isinstance(active_model, dict) and active_model:
        _kv("Active version", active_model.get("version") or active_model.get("active_version"))
    else:
        _kv("Active version", "(none)")

    print("")
    print("Commands:")
    for command in payload.get("commands", []):
        if not isinstance(command, dict):
            print(f"- {_truncate(command)}")
            continue
        print(f"- {command.get('label', '(unknown)')}: {command.get('command', '')}")

    print("")
    print("Paths:")
    for key, value in payload.get("paths", {}).items():
        print(f"- {key}: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local dashboard view renderer for CLI and scripts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    overview = subparsers.add_parser("overview", help="Show the dashboard overview.")
    overview.add_argument("--query", default=None)
    overview.add_argument("--runs-limit", type=int, default=5)
    overview.add_argument("--memory-limit", type=int, default=5)
    overview.add_argument("--snippet-limit", type=int, default=5)
    overview.add_argument("--log-limit", type=int, default=5)

    models = subparsers.add_parser("models", help="Show the model registry.")
    models.add_argument("--limit", type=int, default=10)

    memory = subparsers.add_parser("memory", help="Show recent memory entries.")
    memory.add_argument("--query", default=None)
    memory.add_argument("--limit", type=int, default=10)
    memory.add_argument("--kind", default=None)

    context = subparsers.add_parser("context", help="Show context assembly output.")
    context.add_argument("--query", default=None)
    context.add_argument("--memory-limit", type=int, default=5)
    context.add_argument("--snippet-limit", type=int, default=5)

    logs = subparsers.add_parser("logs", help="Show audit and error logs.")
    logs.add_argument("--limit", type=int, default=5)

    subparsers.add_parser("ops", help="Show the system command and path view.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = _build_app()

    if args.command == "overview":
        render_overview(
            app,
            query=args.query,
            runs_limit=args.runs_limit,
            memory_limit=args.memory_limit,
            snippet_limit=args.snippet_limit,
            log_limit=args.log_limit,
        )
        return 0
    if args.command == "models":
        render_models(app, limit=args.limit)
        return 0
    if args.command == "memory":
        render_memory(app, query=args.query, limit=args.limit, kind=args.kind)
        return 0
    if args.command == "context":
        render_context(
            app, query=args.query, memory_limit=args.memory_limit, snippet_limit=args.snippet_limit
        )
        return 0
    if args.command == "logs":
        render_logs(limit=args.limit)
        return 0
    if args.command == "ops":
        render_ops(app)
        return 0

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
