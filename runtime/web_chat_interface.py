from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from api.server import build_dashboard_routes, create_app
from runtime.dashboard_http import DashboardHttpConfig, build_dashboard_handler
from runtime.chat_interface import ChatSession

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
INDEX_FILE = WEB_ROOT / "index.html"
FAVICON_FILE = WEB_ROOT / "favicon.svg"
ASSET_ROOT = WEB_ROOT / "assets"


def build_handler(session: ChatSession) -> type[BaseHTTPRequestHandler]:
    app = create_app(session=session)
    routes = build_dashboard_routes(app)
    return build_dashboard_handler(
        routes,
        config=DashboardHttpConfig(
            shell_file=INDEX_FILE,
            static_root=ASSET_ROOT,
            favicon_file=FAVICON_FILE,
            serve_shell_fallback=True,
            root_message="AI Lan dashboard",
        ),
    )


def run_web_chat(host: str = "127.0.0.1", port: int = 8765) -> int:
    session = ChatSession()
    handler_class = build_handler(session)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"AI Lan Web Dashboard listening at http://{host}:{port}/overview")
    print("Routes: /overview, /chat, /runs, /models, /memory, /logs, /context, /ops")
    print("Local assets: /assets/css/app.css, /assets/js/app.js, /assets/icons.svg")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web dashboard server.")
    finally:
        server.server_close()
    return 0


__all__ = [
    "build_handler",
    "run_web_chat",
]
