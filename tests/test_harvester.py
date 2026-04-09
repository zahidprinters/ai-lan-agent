import json
from pathlib import Path
from learning.dataset.harvester import HarvestedEntry, harvest_successful_actions


def test_harvest_successful_actions(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    entry = {
        "timestamp": "2026-04-06T00:00:00Z",
        "request": {
            "thought": "test",
            "action": "pc.read_clipboard",
            "args": {},
            "safety_level": "low",
        },
        "result": {
            "status": "executed",
            "action": "pc.read_clipboard",
            "observation": "hello",
            "policy_reason": "ok",
        },
    }
    # Failed entry that should be ignored
    failed_entry = {
        "timestamp": "2026-04-06T00:00:01Z",
        "request": {
            "thought": "fail",
            "action": "web.search",
            "args": {"query": "fail"},
            "safety_level": "low",
        },
        "result": {
            "status": "rejected",
            "action": "web.search",
            "observation": None,
            "policy_reason": "denied",
        },
    }

    with log_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        f.write(json.dumps(failed_entry) + "\n")

    harvested = harvest_successful_actions(log_path)
    assert len(harvested) == 1
    assert harvested[0].action == "pc.read_clipboard"
    assert harvested[0].thought == "test"
    assert harvested[0].observation == "hello"
