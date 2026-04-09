from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from runtime.chat_interface import ChatSession
from runtime.web_chat_interface import build_handler


def _start_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(ChatSession()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _fetch(url: str) -> tuple[int, dict[str, str], bytes]:
    with urlopen(url) as response:
        return response.status, dict(response.headers.items()), response.read()


def test_web_dashboard_serves_local_shell_and_assets() -> None:
    server = _start_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        status, headers, body = _fetch(f"{base_url}/overview")
        assert status == 200
        html = body.decode("utf-8")
        assert 'data-nav="chat"' in html
        assert 'data-nav="runs"' in html
        assert "/assets/js/app.js" in html
        assert "https://" not in html

        status, headers, body = _fetch(f"{base_url}/assets/css/app.css")
        assert status == 200
        assert headers["Content-Type"].startswith("text/css")
        assert "--brand" in body.decode("utf-8")

        status, headers, body = _fetch(f"{base_url}/favicon.svg")
        assert status == 200
        assert headers["Content-Type"].startswith("image/svg+xml")
        assert "<svg" in body.decode("utf-8")

        status, headers, body = _fetch(f"{base_url}/api/state")
        assert status == 200
        payload = json.loads(body.decode("utf-8"))
        assert payload["service"]["name"] == "AI Lan Dashboard"
        assert "session" in payload
    finally:
        server.shutdown()
        server.server_close()
