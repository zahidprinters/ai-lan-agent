from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.model_registry import (  # noqa: E402
    ModelRecord,
    get_active_model,
    init_registry,
    list_registered_models,
    register_model,
    rollback_to_version,
    set_active_model,
)


def record_model_entry(
    model_path: Path,
    *,
    metrics: dict[str, float] | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    registry_path: Path | None = None,
) -> ModelRecord:
    """Compatibility shim around training.model_registry.register_model."""
    return register_model(
        model_path,
        metrics=metrics,
        tags=tags,
        notes=notes,
        registry_path=registry_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model registry and rollback helper.")
    parser.add_argument("--registry", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--model", type=Path, required=True)
    register_parser.add_argument("--metrics", default="{}", help="JSON object")
    register_parser.add_argument("--tags", default="", help="comma-separated")
    register_parser.add_argument("--notes", default="")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("--version", required=True)

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--version", required=True)

    subparsers.add_parser("active")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = init_registry(args.registry)

    if args.command == "register":
        metrics = cast(dict[str, float], json.loads(args.metrics))
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        registered_record = register_model(
            args.model,
            metrics=metrics,
            tags=tags,
            notes=args.notes,
            registry_path=registry,
        )
        print(json.dumps(registered_record.__dict__, indent=2, ensure_ascii=True))
        return

    if args.command == "list":
        records = list_registered_models(registry)
        if args.json:
            print(json.dumps(records, indent=2, ensure_ascii=True))
        else:
            for record in records:
                print(f"{record['version']} -> {record['model_path']}")
        return

    if args.command == "active":
        print(json.dumps(get_active_model(registry), indent=2, ensure_ascii=True))
        return

    if args.command == "activate":
        activated_payload = set_active_model(args.version, registry)
        print(json.dumps(activated_payload, indent=2, ensure_ascii=True))
        return

    if args.command == "rollback":
        rollback_payload = rollback_to_version(args.version, registry)
        print(json.dumps(rollback_payload, indent=2, ensure_ascii=True))
        return


if __name__ == "__main__":
    main()
