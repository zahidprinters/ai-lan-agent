# AI Lan Project Status

**Project Lead:** Nadeem Abbas  
**Status:** Active development (post Phase 3 stabilization)  
**Last Update:** April 11, 2026

## Active Machine Profile

- Current execution baseline: i5-8350U, 16 GB RAM, integrated graphics, CPU-first.
- Active operational lanes: run `X0` to `X4` now, defer `X5`/`X6` heavy workloads to stronger hardware.
- Reference: `docs/PHASE_X_MACHINE_PLAN.md`.

### Phase X Audit Snapshot (2026-04-11)

- Automated audit command: `python scripts/phase_x_audit.py --strict`.
- Latest gate outcome: `X0=pass`, `X1=pass`, `X2=pass`, `X3=manual`, `X4=in_progress`, `X5=deferred`, `X6=deferred`.
- Latest report: `temp/benchmarks/phase_x_audit_report.json`.

## Architecture Snapshot

AI Lan uses a modular layout with direct package folders (not a single `ai_lan.*` namespace package).

| Folder | Responsibility |
| :--- | :--- |
| `training/` | Configuration, dataset split/build, trainer loop, checkpoints, and inference helpers |
| `training/models/` | Bigram, CharMLP, Transformer, LSTM, GRU implementations |
| `tokenizer/` | Character and BPE tokenizers with factory loading/creation |
| `scripts/` | Evaluation, export, quantization, validation, and utility CLIs |
| `tests/` | Unit and integration test coverage |
| `docs/` | User, architecture, configuration, API, deployment, and testing docs |

## What Is Completed

- Stable training/generation flow with reproducible checkpoints.
- Shared checkpoint compatibility loader for export, evaluation, generation, and training resume, with config/tokenizer recovery from checkpoint metadata.
- Multi-architecture model factory and tokenizer factory.
- Run indexing and summary artifacts, including legacy + nested summary normalization and the `all_runs.json` / `all_index.json` compatibility pair.
- ONNX export and dynamic quantization scripts, with quantized checkpoints treated as PyTorch inference-only artifacts.
- Installation validation that checks ONNX tooling and exits nonzero when required packages are missing.
- Sentinel observability (`AI_LAN_DEBUG`, `AI_LAN_TRACE`, `AI_LAN_PROFILE`).
- Sentinel trace sanitization: sensitive variable names and token-like values are masked in trace logs before output.
- Unit test suite passing after cleanup and compatibility fixes.
- Phase 4 action-routing foundation: strict action schema parsing, policy-gated dispatch, and JSONL audit logging.
- Phase 4.1 safety freeze is effectively active: allow/deny/confirmation policy is enforced in router dispatch and now loaded from `config/policies.yaml` (with safe defaults).
- Audit replay capability: dry-run action replay can evaluate historical JSONL audit requests under current policy/router logic without triggering tool side effects.
- Trusted ingestion pipeline foundation: source loading, normalization, dedupe, trust/quality scoring, merged corpus output, and JSON reporting.
- Local memory layer foundation: SQLite-backed memory store, conversation summaries, and deterministic retrieval API.
- Context assembly foundation: prompt-context builder combining memory retrieval and ingestion snippets, now exposed through policy-gated router actions.
- Browser dashboard and JSON state layer: chat session, runs, models, memory, logs, and ops data are now surfaced through the web runtime with route-based local subpages and offline assets.
- Unified local launcher: `scripts/launch.py` now dispatches CLI, Web, and API entrypoints through one shared interface.
- PowerShell dashboard parity: `main.ps1` now mirrors the dashboard categories and includes local Knowledge/System views for models, memory, context, logs, and ops.
- Local dashboard views: `scripts/dashboard_views.py` renders the same Knowledge/System data directly from the CLI.
- Safe adapter expansion (foundation): added read-only PC status/process actions and initial Android adapter surface with strict allowlist, confirmation gating, and safe-mode side-effect guard.
- Phase 4.2 Android hardening slice: package launches now require an explicit package allowlist, optional device allowlists can pin side-effect actions to known ADB targets, and Android screenshot output is constrained to `temp/`.
- Phase 4.2 reliability hardening slice: Android ADB calls now use bounded timeout handling with deterministic timeout failures, and PC process listing now uses bounded timeout handling with deterministic unavailable responses.
- Phase 4.2 ingestion enforcement slice: ingestion pipeline now enforces a minimum final score threshold during merge and reports low-score filtered document counts.
- Phase 4.2 exit gate completed: integration tests now cover router -> policy -> adapter reliability paths plus ingestion trust filtering behavior.
- Evaluation and autonomy scaffolding (foundation): added tool benchmark harness plus offline learning/model registry scaffolds.
- Offline-learning promotion guardrail: placeholder candidate artifacts are blocked from model-registry promotion.
- Embodied AI roadmap foundation: documented CPU-first vision, speech, and local reasoning shortlist plus future `perception/vision/` and `perception/audio/` package split.
- Phase 4.4 RL-01 reflection reliability slice: ReAct runtime now performs bounded self-correction retries for recoverable tool failures with repeated-action suppression and deterministic stop reasons.
- Phase 4.4 RL-02 verification reliability slice: selected side-effect actions now attach explicit post-action verification metadata so launch requests do not silently count as trustworthy outcomes.
- Phase 4.4 RL-03 guardrail benchmarking slice: model promotion now requires a per-version quality artifact in `runs/quality/` and blocks activation on missing, below-threshold, or below-baseline scores.
- Phase 4.4 RL-04 dynamic safety slice: runtime context now emits `sensitive_context` and policy evaluation escalates selected risky actions to strong confirmation in sensitive contexts.
- Phase 4.4 RL-05 replay reliability slice: audit replay now emits deterministic matched/diverged/skipped summaries, supports strict failure mode, and is wired into CI for router/policy changes.
- Phase 4.4 RL-06 graceful degradation slice: llama-cpp planning now fails over deterministically to classic generation with debug-safe fallback metadata so user turns do not stall on local-brain failures.
- Phase 4.4 RL-07 health dashboard slice: dashboard/API now expose runtime health telemetry for CPU pressure proxy, RAM usage, and model confidence summary through `/api/health` and the `/health` dashboard tab.

## Cleanup and Quality Enhancements (Latest)

- Removed legacy/unneeded code paths and unused imports.
- Removed obsolete backward-compatibility alias in transformer model.
- Improved checkpoint compatibility by recovering config/tokenizer metadata from saved checkpoints and normalizing mixed legacy/new run summaries.
- Cleaned temporary/cache artifacts from workspace.
- Reduced default test overhead by avoiding global trace/profile activation.
- Aligned dependency grouping: base runtime vs dev/optional experiment tracking.
- Verified deployment runtime sync in the active `.venv`, including `onnxruntime==1.20.1` for ONNX CPU inference.

## Known Intentional Stubs

The following modules remain early Phase 4 surfaces and are intentionally limited/safe by design:

- `tools/pc_control.py`

These are retained by design and are not duplicate/legacy remnants.

## Placeholder and Compatibility Boundaries

- Placeholder modules (future-facing): selected areas in `core/inference/`, `runtime/`, `tools/perception/`, `memory/long_term/`, and `learning/` are scaffolds for Phase 4/5 and may intentionally expose limited behavior.
- Compatibility surfaces (migration-only): facades such as `tools/web/fetch.py`, `tools/web/clean.py`, and `learning/registry/model_registry.py` remain to preserve import stability while internals move to package-layer implementations.
- Active runtime surfaces (current source of truth): `api/`, `router/`, `tools/web/search.py`, `tools/memory_store.py`, `tools/web_ingest.py`, `safety/`, and the Phase 3 training stack under `training/` and `tokenizer/`.
- Legacy snapshot has been retired from the active tree; historical migration context now lives in the repository history and docs.

## Next Priorities

1. **Phase 4.3:** completed (2026-04-11). Benchmark harness exit gate now includes curated CI thresholds, checked-in trace regression coverage, category coverage minimums, per-category success thresholds, and distinct action diversity thresholds.
2. **Phase 4.5A (Reasoning-first):** completed (2026-04-11). Exit-gated with model-validated planning, stream-trigger orchestration, runtime guard + execution-contract enforcement, pressure-aware routing fallback, upgraded context compaction quality, and strict benchmark assertions for runtime guard/routing/execution-contract/compaction behavior.
3. **Phase 4.5B (Embodied runtime):** completed (2026-04-11). Runtime perception now includes bounded capture depth, confidence-filtered OCR summaries, OCR backend selection/fallback controls (`auto`/`tesseract`/`easyocr`), optional OpenCV preprocessing, and session/context metadata propagation (`source`, `confidence`, `ocr_backend`) without bypassing router/policy ownership.
4. **Phase 5.1:** active (kickoff). Persistent memory backend integration is in place with initial retention/user-control boundaries (`memory_retention_days`, `memory_max_entries`) and CLI prune flow (`scripts/memory_store.py prune`); continue with broader retrieval-quality and policy-boundary hardening.
5. **Phase 5.2+:** ship nightly offline learning with canary promotion gates, benchmark-regression blocking, model registry rollback, and orchestration hardening when workload scale requires it.

Direction lock: 4.5A and 4.5B are complete; keep reasoning/safety regression gates preserved while moving into Phase 5 memory and offline-learning execution.

## Strategic Reliability Pillars

- Reflection Layer (Self-Correction)
- State Verification (Trust but Verify)
- Automated Guardrail Benchmarking
- Dynamic Safety Policy (Context-Aware)
- Deterministic Dry-Run Replay

Implementation ticket pack:

- `docs/superpowers/todos/2026-04-10-phase-4-4-reliability-tickets.md`
