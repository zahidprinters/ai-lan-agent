---
description: "Run a complete router safety gate workflow for dispatch changes: schema validation, policy decision path, confirmation behavior, replay gate verification, and docs sync."
name: "Router Change Gate"
argument-hint: "Describe the router/safety change and expected behavior, including any new action name and confirmation policy."
agent: "agent"
---
Implement and validate a router/safety change end-to-end in one workflow.

Scope:
- Router dispatch behavior, schema parsing/normalization, safety policy, confirmation flow, and audit replay integrity.

Required workflow:
1. Inspect current behavior in `router/schema.py`, `router/dispatch_core.py`, `router/router.py`, `safety/policy_engine.py`, and relevant tests.
2. Implement the minimal safe change.
3. Add or update tests that cover:
   - accepted path
   - denied path
   - confirmation-required path
   - dry-run behavior when relevant
4. Run verification commands:
   - `python -m pytest tests/test_action_router.py -q --disable-warnings`
   - `python -m pytest tests/test_dynamic_safety.py -q --disable-warnings`
   - `python -m pytest tests/test_audit_replay.py -q --disable-warnings`
   - `python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict`
5. If behavior is user-visible or config-driven, update docs in the same change:
   - `docs/SECURITY_POLICY.md`
   - `docs/API_REFERENCE.md`
   - `docs/TESTING_GUIDELINES.md`
   - `docs/CONFIGURATION.md`

Safety requirements:
- Do not bypass policy checks, confirmation checks, or audit logging.
- Keep policy source-of-truth aligned with `config/policies.yaml` and `safety/policy_engine.py`.
- Preserve deterministic replay behavior.

Final response requirements:
- Summarize behavior change and safety posture.
- List tests and replay command results.
- Call out any residual risks or unverified paths.
