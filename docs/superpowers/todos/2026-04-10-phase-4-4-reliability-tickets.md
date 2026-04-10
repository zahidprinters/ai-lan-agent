# Phase 4.4 Reliability Tickets

Date: 2026-04-10
Owner: AI Lan core team
Status: Ready for implementation

## Scope

This ticket pack converts the Phase 4.4 reliability update into concrete implementation work for:

1. Reflection Layer (self-correction)
2. State Verification (trust but verify)
3. Guardrail Benchmarking (regression blocking)
4. Dynamic Safety Policy (context-aware)
5. Deterministic Dry-Run Replay (change gate)

---

## Ticket RL-01: Reflection Layer In ReAct Controller

Priority: P0

Objective:

- Add bounded self-correction when a tool call fails or returns inconsistent observations.

Implementation:

- Update `agents/react/agent.py` and `agents/react/controller.py`.
- Add a reflection branch:
  - Detect failed tool outcomes (`status in {"failed", "blocked", "blocked_policy", "adb_unavailable"}` and empty/invalid observations).
  - Generate one recovery step with adjusted args/query.
  - Enforce strict retry budget (default: 1 retry per step, 3 retries per turn max).
- Add repeated-action suppression so reflection cannot loop infinitely.

Acceptance Criteria:

- Agent does not get stuck on repeating failed tool calls.
- On recoverable failures, agent attempts an alternative once and continues.
- On unrecoverable failures, agent exits with explicit reason and safe final response.

Tests:

- Add tests in `tests/test_chat_interface.py` and `tests/test_layered_modules.py`:
  - failed tool -> one reflection retry
  - repeated failure -> bounded stop
  - successful retry -> proceeds to final answer

---

## Ticket RL-02: Post-Action State Verification

Priority: P0

Objective:

- Verify that side-effect actions actually changed real state.

Implementation:

- Add verification registry in `router/dispatch_core.py`.
- For selected actions, run read-only verification tools after execution:
  - `pc.open_app` -> verify with `pc.list_running_apps`
  - `android.launch_app` -> verify with `android.list_devices` plus launch command output checks
- Extend `ActionExecutionResult.observation` with:
  - `verification_status` (`verified`, `not_verified`, `verification_failed`)
  - `verification_detail`

Acceptance Criteria:

- Side-effect action responses include verification metadata.
- Verification failures are explicit and do not silently pass.

Tests:

- Extend `tests/test_action_router.py`:
  - successful action + verified state
  - action executed but verification failed
  - verification tool error path

---

## Ticket RL-03: Guardrail Quality Benchmark Gate

Priority: P1

Objective:

- Block candidate model promotion when quality regresses below baseline.

Implementation:

- Add `scripts/benchmark_quality.py`.
- Add standard prompt suite file `data/benchmarks/quality_prompts.json` (50 prompts split by logic/math/tool-choice).
- Emit score artifact under `runs/quality/`.
- Integrate gate with model promotion flow in:
  - `training/model_registry.py`
  - `scripts/model_registry.py`
- Add threshold config in `config/settings.yaml`:
  - `quality_guardrail_min_score`
  - `quality_guardrail_baseline_model`

Acceptance Criteria:

- Promotion command fails if candidate score is below threshold/baseline.
- Score artifacts are persisted and traceable.

Tests:

- Add `tests/test_quality_guardrail.py`:
  - pass path (promotion allowed)
  - fail path (promotion blocked)
  - missing benchmark artifact path

---

## Ticket RL-04: Dynamic Context-Aware Safety

Priority: P1

Objective:

- Elevate safety requirements automatically in sensitive contexts.

Implementation:

- Update `safety/policy_engine.py`:
  - ingest compact perception signal from runtime context (`sensitive_context=true`).
  - when sensitive context is active, promote risky actions to high safety.
- Extend decision model to support `requires_strong_confirmation`.
- Wire context input from `runtime/perception_loop.py` and `runtime/context.py`.
- Add setting flags in `config/settings.yaml`:
  - `dynamic_safety_enabled`
  - `sensitive_context_keywords`

Acceptance Criteria:

- Typing/screenshot actions require stronger confirmation under sensitive context.
- Normal context behavior remains unchanged.

Tests:

- Add `tests/test_dynamic_safety.py`:
  - sensitive context -> stronger confirmation required
  - non-sensitive context -> existing confirmation behavior

---

## Ticket RL-05: Deterministic Replay Gate In CI Workflow

Priority: P0

Objective:

- Make policy/router changes replay-validated before merge/release.

Implementation:

- Extend `scripts/replay_audit.py`:
  - deterministic summary output (matched, diverged, skipped)
  - strict nonzero exit on divergence when `--strict` is enabled
- Add CI wiring in `.github/workflows/ci.yml`:
  - run replay gate on policy/router touching changes
- Add replay fixture bundle in `tests/fixtures/replay/`.

Acceptance Criteria:

- Replay gate can run in strict mode and fail on unexpected decision drift.
- Output includes machine-readable summary JSON.

Tests:

- Extend `tests/test_audit_replay.py`:
  - strict pass
  - strict fail
  - deterministic output equivalence

---

## Ticket RL-06: Graceful Degradation For Local Brain Failures

Priority: P1

Objective:

- Ensure local runtime never becomes non-responsive when llama-cpp fails.

Implementation:

- Update `agents/react/controller.py` and `core/inference/local_reasoning.py`:
  - on llama load/run failure, immediately fallback to deterministic/classic mode
  - surface fallback reason in debug-safe response metadata

Acceptance Criteria:

- No user turn ends with empty response due to local-brain failure.

Tests:

- Extend `tests/test_local_reasoning.py` fallback paths.

---

## Ticket RL-07: Health Dashboard Tab

Priority: P2

Objective:

- Expose operational health signals in dashboard/API.

Implementation:

- Add health endpoint in `api/server.py` and runtime provider in `runtime/dashboard_http.py`.
- Add web route/tab under `web/` for:
  - CPU pressure/thermal proxy
  - RAM usage
  - model confidence summary

Acceptance Criteria:

- Health tab available in web dashboard and JSON endpoint.

Tests:

- Extend `tests/test_dashboard_api.py`.

---

## Delivery Order (Recommended)

1. RL-01 Reflection Layer
2. RL-02 State Verification
3. RL-05 Deterministic Replay Gate
4. RL-03 Guardrail Benchmarking
5. RL-04 Dynamic Safety
6. RL-06 Graceful Degradation
7. RL-07 Health Dashboard

## Definition Of Done (Phase 4.4)

- RL-01, RL-02, RL-05 are complete and merged.
- Unit and non-integration suites pass.
- Replay strict mode is active for policy/router changes.
- Docs updated in `ROADMAP.md`, `docs/AI_CONTEXT.md`, `docs/PROJECT_STATUS.md`, and `docs/API_REFERENCE.md` where behavior changed.
