import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any
from debug_utils import sentinel


@dataclass
class HarvestedEntry:
    thought: str
    action: str
    args: dict[str, Any]
    observation: Any


@sentinel
def harvest_successful_actions(log_path: Path) -> list[HarvestedEntry]:
    """Extracts successful tool actions from the audit log."""
    if not log_path.exists():
        return []
    results = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Check for successful execution
                if data.get("result", {}).get("status") == "executed":
                    req = data.get("request", {})
                    # Ensure all required fields are present
                    if "thought" in req and "action" in req and "args" in req:
                        results.append(
                            HarvestedEntry(
                                thought=req["thought"],
                                action=req["action"],
                                args=req["args"],
                                observation=data["result"].get("observation"),
                            )
                        )
            except (json.JSONDecodeError, KeyError):
                continue
    return results


__all__ = ["HarvestedEntry", "harvest_successful_actions"]
