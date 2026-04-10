from __future__ import annotations

import argparse

from _bootstrap import ensure_repo_root

ensure_repo_root()

from api.server import run_api_server
from runtime.chat_interface import run_chat_cli
from runtime.voice_chat_interface import run_voice_chat_cli
from runtime.web_chat_interface import run_web_chat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified launcher for the AI Lan CLI, Web, and API entrypoints.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=("cli", "voice", "web", "api"),
        default="cli",
        help="Which interface to start.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for web/api modes.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind for web/api modes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.mode == "cli":
        return run_chat_cli()
    if args.mode == "voice":
        return run_voice_chat_cli()
    if args.mode == "web":
        return run_web_chat(host=args.host, port=args.port)
    if args.mode == "api":
        return run_api_server(host=args.host, port=args.port)

    raise SystemExit(f"Unsupported launch mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
