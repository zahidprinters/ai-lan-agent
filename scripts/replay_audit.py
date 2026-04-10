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
    outcome: str
    previous_policy_reason: str
    replay_policy_reason: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "previous_status": self.previous_status,
            "replay_status": self.replay_status,
            "previous_decision": self.previous_decision,
            "replay_decision": self.replay_decision,
            "decision_match": self.decision_match,
            "outcome": self.outcome,
            "previous_policy_reason": self.previous_policy_reason,
            "replay_policy_reason": self.replay_policy_reason,
            "error": self.error,
        }


def _build_skipped_row(
    index: int,
    *,
    action: str = "unknown",
    previous_status: str = "unknown",
    previous_policy_reason: str = "",
    error: str,
) -> ReplayRow:
    return ReplayRow(
        index=index,
        action=action,
        previous_status=previous_status,
        replay_status="skipped",
        previous_decision=_decision_bucket(previous_status),
        replay_decision="skipped",
        decision_match=False,
        outcome="skipped",
        previous_policy_reason=previous_policy_reason,
        replay_policy_reason="",
        error=error,
    )


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
    total_rows = 0

    for index, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        total_rows += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            parse_errors += 1
            rows.append(
                _build_skipped_row(index, error=f"invalid_json: {exc.msg}")
            )
            continue

        try:
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
                    outcome=(
                        "matched" if previous_decision == replay_decision else "diverged"
                    ),
                    previous_policy_reason=previous_policy_reason,
                    replay_policy_reason=replay_result.policy_reason,
                )
            )
        except Exception as exc:
            request_obj = payload.get("request") if isinstance(payload, dict) else None
            action_name = "unknown"
            if isinstance(request_obj, dict):
                action_name = str(request_obj.get("action", "unknown"))
            previous_result = payload.get("result", {}) if isinstance(payload, dict) else {}
            previous_status = str(previous_result.get("status", "unknown"))
            previous_policy_reason = str(previous_result.get("policy_reason", ""))
            rows.append(
                _build_skipped_row(
                    index,
                    action=action_name,
                    previous_status=previous_status,
                    previous_policy_reason=previous_policy_reason,
                    error=f"replay_error: {exc}",
                )
            )

    matched = sum(1 for row in rows if row.outcome == "matched")
    diverged = sum(1 for row in rows if row.outcome == "diverged")
    skipped = sum(1 for row in rows if row.outcome == "skipped")
    compared = matched + diverged
    mismatches = [row.to_dict() for row in rows if row.outcome == "diverged"]
    skipped_rows = [row.to_dict() for row in rows if row.outcome == "skipped"]
    report = {
        "input": str(input_path),
        "total_rows": total_rows,
        "parsed_rows": total_rows - parse_errors,
        "parse_errors": parse_errors,
        "summary": {
            "matched": matched,
            "diverged": diverged,
            "skipped": skipped,
        },
        "decision_match_rate": round(matched / compared, 4) if compared else 0.0,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "skipped_rows": skipped_rows,
        "rows": [row.to_dict() for row in rows],
    }
    return report


def should_fail_strict(report: dict[str, Any]) -> bool:
    summary = report.get("summary", {})
    return bool(int(summary.get("diverged", 0)) or int(summary.get("skipped", 0)))


def write_replay_report(output_path: Path, report: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


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
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when replay detects divergence or skipped rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = replay_audit_log(args.input, assume_confirmed=args.assume_confirmed)
    write_replay_report(args.output, report)
    strict_failed = args.strict and should_fail_strict(report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "summary": report.get("summary", {}),
                "strict": args.strict,
                "strict_failed": strict_failed,
            },
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 1 if strict_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
