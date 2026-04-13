from __future__ import annotations

import argparse
import os

from _bootstrap import ensure_repo_root

ensure_repo_root()

from api.server import create_app, run_api_server
from runtime.chat_interface import ChatSession, run_chat_cli
from runtime.voice_chat_interface import run_voice_chat_cli
from runtime.web_chat_interface import run_web_chat
from runtime.session import VALID_DEVICE_TYPES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified launcher for the AI Lan CLI, Web, API, Companion, and Satellite entrypoints.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=("cli", "voice", "web", "api", "companion", "satellite"),
        default="cli",
        help=(
            "Which interface to start. "
            "'companion' and 'satellite' run the API server with their device_type "
            "recorded in the session (companion: port 8766, satellite: port 8767 by default)."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for web/api/companion/satellite modes.")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (defaults: web/api=8765, companion=8766, satellite=8767).")
    parser.add_argument(
        "--profile",
        default="default",
        help="User context profile name scoped to this session (e.g. 'work', 'home').",
    )
    return parser


_MODE_DEFAULT_PORTS: dict[str, int] = {
    "web": 8765,
    "api": 8765,
    "companion": 8766,
    "satellite": 8767,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile: str = args.profile.strip() or "default"

    if args.mode == "cli":
        os.environ.setdefault("AI_LAN_DEVICE_TYPE", "cli")
        os.environ.setdefault("AI_LAN_PROFILE", profile)
        return run_chat_cli()

    if args.mode == "voice":
        os.environ.setdefault("AI_LAN_DEVICE_TYPE", "voice")
        os.environ.setdefault("AI_LAN_PROFILE", profile)
        return run_voice_chat_cli()

    if args.mode == "web":
        os.environ.setdefault("AI_LAN_DEVICE_TYPE", "web")
        os.environ.setdefault("AI_LAN_PROFILE", profile)
        port = args.port if args.port is not None else _MODE_DEFAULT_PORTS["web"]
        return run_web_chat(host=args.host, port=port)

    if args.mode in {"api", "companion", "satellite"}:
        device_type = args.mode
        port = args.port if args.port is not None else _MODE_DEFAULT_PORTS[device_type]
        session = ChatSession(device_type=device_type, profile=profile)
        app = create_app(session=session)
        return run_api_server(host=args.host, port=port, app=app)

    raise SystemExit(f"Unsupported launch mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())

