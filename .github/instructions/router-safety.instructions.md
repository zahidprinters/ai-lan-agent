---
description: "Use when editing router, safety, or action-dispatch code in this repo. Covers policy checks, confirmation rules, schema-first changes, audit logging, and legacy compatibility across router/ and safety/."
name: "Router And Safety"
applyTo:
	- "router/**/*.py"
	- "safety/**/*.py"
---
# Router And Safety Guidelines

- Preserve the separation of concerns: agents decide, router dispatches, safety evaluates, tools execute.
- For any new action or tool path, follow the repository flow: define schema, define policy/confirmation behavior, implement a safe stub, register it, then add tests.
- Default new capabilities to read-only or confirmation-gated behavior until the policy explicitly allows more.
- Do not bypass policy evaluation, confirmation handling, or audit logging for convenience paths or fallback logic.
- Keep policy behavior source-of-truth in `config/policies.yaml` (`allow_actions`, `deny_actions`, `require_confirmation`) and preserve safe fallback defaults in `safety/policy_engine.py`.
- Keep compatibility with the layered scaffold and the legacy action/tool paths. If a change touches dispatch behavior, verify you are not breaking the fallback path described in [docs/PROJECT_STRUCTURE.md](../../docs/PROJECT_STRUCTURE.md).
- Prefer explicit, typed payloads and existing schema helpers over ad hoc dictionaries or string parsing.
- When a change affects action results, safety decisions, or normalization behavior, add focused tests for both accepted and rejected or confirmation-required paths.
- If dispatch semantics change, validate both live execution and dry-run (`dispatch_agent_action(..., dry_run=True)`) behavior.
- Keep external integrations behind local facades and check [docs/OPEN_SOURCE_REFERENCE.md](../../docs/OPEN_SOURCE_REFERENCE.md) before adding a dependency to the dispatch stack.
- Use [docs/AI_GUIDELINES.md](../../docs/AI_GUIDELINES.md), [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), and [docs/PROJECT_STRUCTURE.md](../../docs/PROJECT_STRUCTURE.md) as the primary references instead of re-deriving rules from scattered code.

## Required Dispatch Checks

- Schema parse/validation still rejects malformed actions.
- Policy outcome is explicit (`allow`, `deny`, or `confirmation_required`) and surfaced to caller.
- Audit logging occurs for both success and refusal paths.
- Dry-run dispatch (`status="dry_run"`) never executes side-effect handlers.
- Audit replay (`scripts/replay_audit.py`) compares decisions deterministically against historical JSONL requests.
- Fallback compatibility remains intact where legacy path is expected.

## Confirmation And Denial Rules

- If an action can change host/device state, require confirmation unless policy explicitly marks it safe.
- If an action is denied, return deterministic refusal output rather than partial execution.
- Keep policy reasoning traceable so tests can assert expected decision behavior.

## Validation Commands

- Minimum after router/safety edits:
	- targeted tests for changed modules, then `python -m pytest tests -m unit -q --disable-warnings`
- Before finishing broader dispatch refactors:
	- `python -m pytest tests -q --disable-warnings --ignore=tests/integration`