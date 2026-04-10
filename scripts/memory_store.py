from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from debug_utils import sentinel
from tools.memory_store import (
    add_memory_entry,
    get_recent_memories,
    init_memory_store,
    retrieve_relevant_memories,
    store_conversation_summary,
)


@sentinel
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local memory store utility for AI Lan.")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Optional path to the SQLite memory store. Defaults to temp/memory/memory_store.sqlite3.",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Optional memory backend override (none or chroma).",
    )
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=None,
        help="Optional Chroma persistence path when backend is set to chroma.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a general memory entry.")
    add_parser.add_argument("--kind", required=True)
    add_parser.add_argument("--content", required=True)
    add_parser.add_argument("--metadata", default="{}", help="JSON object string")

    convo_parser = subparsers.add_parser(
        "add-conversation", help="Add a conversation summary entry."
    )
    convo_parser.add_argument("--user", required=True)
    convo_parser.add_argument("--assistant", required=True)
    convo_parser.add_argument("--metadata", default="{}", help="JSON object string")

    search_parser = subparsers.add_parser("search", help="Retrieve relevant memories for a query.")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--min-score", type=float, default=0.05)
    search_parser.add_argument("--kind", default=None)

    recent_parser = subparsers.add_parser("recent", help="List recent memory entries.")
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.add_argument("--kind", default=None)

    return parser.parse_args()


@sentinel
def main() -> None:
    args = parse_args()
    db_path = init_memory_store(args.db)

    if args.command == "add":
        entry = add_memory_entry(
            kind=args.kind,
            content=args.content,
            metadata=json.loads(args.metadata),
            db_path=db_path,
            memory_backend=args.backend,
            chroma_path=args.chroma_path,
        )
        print(f"added memory_id={entry.memory_id} kind={entry.kind}")
        return

    if args.command == "add-conversation":
        entry = store_conversation_summary(
            user_text=args.user,
            assistant_text=args.assistant,
            metadata=json.loads(args.metadata),
            db_path=db_path,
            memory_backend=args.backend,
            chroma_path=args.chroma_path,
        )
        print(f"added conversation memory_id={entry.memory_id}")
        return

    if args.command == "search":
        hits = retrieve_relevant_memories(
            query=args.query,
            limit=args.limit,
            min_score=args.min_score,
            kind=args.kind,
            db_path=db_path,
            memory_backend=args.backend,
            chroma_path=args.chroma_path,
        )
        print(json.dumps([hit.to_dict() for hit in hits], indent=2, ensure_ascii=True))
        return

    if args.command == "recent":
        entries = get_recent_memories(
            limit=args.limit,
            kind=args.kind,
            db_path=db_path,
        )
        print(
            json.dumps(
                [
                    {
                        "memory_id": entry.memory_id,
                        "kind": entry.kind,
                        "summary": entry.summary,
                        "metadata": entry.metadata,
                        "created_at": entry.created_at,
                    }
                    for entry in entries
                ],
                indent=2,
                ensure_ascii=True,
            )
        )
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
