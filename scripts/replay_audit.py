from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from router.dispatch_core import ActionExecutionResult, dispatch_agent_action


@dataclass(frozen=True)
class ReplayRow:
    index: int
    action: str
    previous_status: str
    replay_status: str
    previous_decision: str
    replay_decision: str
    decision_match: bool
    previous_policy_reason: str
    replay_policy_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "previous_status": self.previous_status,
            "replay_status": self.replay_status,
            "previous_decision": self.previous_decision,
            "replay_decision": self.replay_decision,
            "decision_match": self.decision_match,
            "previous_policy_reason": self.previous_policy_reason,
            "replay_policy_reason": self.replay_policy_reason,
        }


def _decision_bucket(status: str) -> str:
    if status in {"executed", "dry_run"}:
        return "allowed"
    if status == "confirmation_required":
        return "confirmation_required"
    if status == "rejected":
        return "rejected"
    return "other"


def _infer_confirmed(previous_status: str, assume_confirmed: bool) -> bool:
    if assume_confirmed:
        return True
    return previous_status == "executed"


def replay_audit_log(
    input_path: Path,
    *,
    assume_confirmed: bool = False,
) -> dict[str, Any]:
    if not input_path.exists():
        raise FileNotFoundError(f"Audit log not found: {input_path}")

    rows: list[ReplayRow] = []
    parse_errors = 0

    for index, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            request = payload["request"]
            previous_result = payload.get("result", {})
            previous_status = str(previous_result.get("status", "unknown"))
            previous_policy_reason = str(previous_result.get("policy_reason", ""))

            confirmed = _infer_confirmed(previous_status, assume_confirmed)
            replay_result: ActionExecutionResult = dispatch_agent_action(
                request,
                confirmed=confirmed,
                dry_run=True,
                log_to_audit=False,
            )

            previous_decision = _decision_bucket(previous_status)
            replay_decision = _decision_bucket(replay_result.status)
            rows.append(
                ReplayRow(
                    index=index,
                    action=str(request.get("action", "unknown")),
                    previous_status=previous_status,
                    replay_status=replay_result.status,
                    previous_decision=previous_decision,
                    replay_decision=replay_decision,
                    decision_match=previous_decision == replay_decision,
                    previous_policy_reason=previous_policy_reason,
                    replay_policy_reason=replay_result.policy_reason,
                )
            )
        except Exception:
            parse_errors += 1

    total = len(rows)
    matched = sum(1 for row in rows if row.decision_match)
    mismatches = [row.to_dict() for row in rows if not row.decision_match]
    report = {
        "input": str(input_path),
        "total_rows": total,
        "parsed_rows": total,
        "parse_errors": parse_errors,
        "decision_match_rate": round(matched / total, 4) if total else 0.0,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay action audit log in dry-run mode to compare policy decisions."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "temp" / "action_audit.jsonl",
        help="Path to action audit JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "temp" / "benchmarks" / "audit_replay_report.json",
        help="Path to write replay report JSON.",
    )
    parser.add_argument(
        "--assume-confirmed",
        action="store_true",
        help="Treat all replayed requests as user-confirmed where confirmation could apply.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = replay_audit_log(args.input, assume_confirmed=args.assume_confirmed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": report}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
