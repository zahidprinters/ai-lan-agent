from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class DashboardRouteSet:
    health: Callable[[], JsonDict]
    session: Callable[[], JsonDict]
    state: Callable[[str | None, int, int, int, int], JsonDict]
    runs: Callable[[int, bool], JsonDict]
    models: Callable[[], JsonDict]
    memory: Callable[[str | None, int, str | None], JsonDict]
    context: Callable[[str | None, int, int], JsonDict]
    logs: Callable[[int], JsonDict]
    ops: Callable[[], JsonDict]
    chat: Callable[[str], JsonDict]


@dataclass(frozen=True)
class DashboardHttpConfig:
    shell_file: Path | None = None
    static_root: Path | None = None
    favicon_file: Path | None = None
    serve_shell_fallback: bool = False
    root_message: str = "AI Lan dashboard API"


def _json_bytes(payload: JsonDict) -> bytes:
    return json.dumps(payload, ensure_ascii=True, indent=2, default=str).encode("utf-8")


def _query_value(params: dict[str, list[str]], key: str, default: str = "") -> str:
    values = params.get(key)
    if not values:
        return default
    value = values[0].strip()
    return value if value else default


def _safe_int(raw: str | None, default: int) -> int:
    try:
        return max(int(raw or default), 1)
    except (TypeError, ValueError):
        return max(default, 1)


def _guess_content_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(str(path))
    return content_type or "application/octet-stream"


def _resolve_child_path(root: Path, request_path: str, prefix: str) -> Path | None:
    relative = unquote(request_path.removeprefix(prefix))
    if not relative:
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def build_dashboard_handler(
    routes: DashboardRouteSet,
    *,
    config: DashboardHttpConfig | None = None,
) -> type[BaseHTTPRequestHandler]:
    resolved_config = config or DashboardHttpConfig()

    class DashboardHandler(BaseHTTPRequestHandler):
        def _send_bytes(
            self,
            payload: bytes,
            *,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
            cache_control: str = "no-store",
        ) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", cache_control)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: JsonDict, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send_bytes(
                _json_bytes(payload),
                content_type="application/json; charset=utf-8",
                status=status,
            )

        def _send_file(
            self,
            path: Path,
            *,
            content_type: str | None = None,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            if not path.exists() or not path.is_file():
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_bytes(
                path.read_bytes(),
                content_type=content_type or _guess_content_type(path),
                status=status,
                cache_control="no-store",
            )

        def _serve_shell(self) -> None:
            if resolved_config.shell_file is None:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_file(resolved_config.shell_file, content_type="text/html; charset=utf-8")

        def _serve_api_root(self) -> None:
            self._send_json({"status": "ok", "message": resolved_config.root_message})

        def _handle_state_query(self, params: dict[str, list[str]]) -> None:
            self._send_json(
                routes.state(
                    _query_value(params, "query"),
                    _safe_int(_query_value(params, "runs_limit"), 10),
                    _safe_int(_query_value(params, "memory_limit"), 10),
                    _safe_int(_query_value(params, "snippet_limit"), 5),
                    _safe_int(_query_value(params, "log_limit"), 25),
                )
            )

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            path = unquote(parsed.path or "/")

            if path in {"/", "/index.html"}:
                if resolved_config.serve_shell_fallback:
                    self._serve_shell()
                else:
                    self._serve_api_root()
                return
            if path == "/api/health":
                self._send_json(routes.health())
                return
            if path == "/api/session":
                self._send_json(routes.session())
                return
            if path == "/api/state":
                self._handle_state_query(params)
                return
            if path == "/api/runs":
                self._send_json(
                    routes.runs(
                        _safe_int(_query_value(params, "limit"), 10),
                        _query_value(params, "all", "0") in {"1", "true", "True"},
                    )
                )
                return
            if path == "/api/models":
                self._send_json(routes.models())
                return
            if path == "/api/memory":
                self._send_json(
                    routes.memory(
                        _query_value(params, "query"),
                        _safe_int(_query_value(params, "limit"), 10),
                        _query_value(params, "kind") or None,
                    )
                )
                return
            if path == "/api/context":
                self._send_json(
                    routes.context(
                        _query_value(params, "query"),
                        _safe_int(_query_value(params, "memory_limit"), 5),
                        _safe_int(_query_value(params, "snippet_limit"), 5),
                    )
                )
                return
            if path == "/api/logs":
                self._send_json(routes.logs(_safe_int(_query_value(params, "limit"), 25)))
                return
            if path == "/api/ops":
                self._send_json(routes.ops())
                return
            if path.startswith("/assets/") and resolved_config.static_root is not None:
                asset_path = _resolve_child_path(resolved_config.static_root, path, "/assets/")
                if asset_path is None:
                    self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_file(asset_path)
                return
            if path == "/favicon.svg" and resolved_config.favicon_file is not None:
                self._send_file(resolved_config.favicon_file, content_type="image/svg+xml")
                return
            if resolved_config.serve_shell_fallback and not path.startswith("/api/"):
                self._serve_shell()
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/api/chat":
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return

            length_raw = self.headers.get("Content-Length", "0")
            try:
                length = int(length_raw)
            except ValueError:
                self._send_json({"error": "Invalid content length"}, status=HTTPStatus.BAD_REQUEST)
                return

            raw = self.rfile.read(max(length, 0))
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json({"error": "Invalid JSON payload"}, status=HTTPStatus.BAD_REQUEST)
                return

            if not isinstance(payload, dict):
                self._send_json(
                    {"error": "Payload must be an object"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            message_obj = payload.get("message")
            if not isinstance(message_obj, str):
                self._send_json(
                    {"error": "Field 'message' must be a string"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            self._send_json(routes.chat(message_obj))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    return DashboardHandler


__all__ = [
    "DashboardHttpConfig",
    "DashboardRouteSet",
    "build_dashboard_handler",
]
