# AI Lan Project Status

**Project Lead:** Nadeem Abbas  
**Status:** Active development (post Phase 3 stabilization)  
**Last Update:** April 10, 2026

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
- Evaluation and autonomy scaffolding (foundation): added tool benchmark harness plus offline learning/model registry scaffolds.
- Offline-learning promotion guardrail: placeholder candidate artifacts are blocked from model-registry promotion.
- Embodied AI roadmap foundation: documented CPU-first vision, speech, and local reasoning shortlist plus future `perception/vision/` and `perception/audio/` package split.
- Phase 4.4 RL-01 reflection reliability slice: ReAct runtime now performs bounded self-correction retries for recoverable tool failures with repeated-action suppression and deterministic stop reasons.
- Phase 4.4 RL-02 verification reliability slice: selected side-effect actions now attach explicit post-action verification metadata so launch requests do not silently count as trustworthy outcomes.
- Phase 4.4 RL-05 replay reliability slice: audit replay now emits deterministic matched/diverged/skipped summaries, supports strict failure mode, and is wired into CI for router/policy changes.

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

1. **Phase 4.2:** harden PC/Android/ingestion adapters from safe stubs to production-safe allowlisted implementations.
2. **Phase 4.3:** enforce offline + online-style evaluation gates (tool success, refusal quality, latency) in CI.
3. **Phase 4.4:** add production-grade reliability controls: reflection-based self-correction, post-action state verification, and deterministic dry-run replay gating for policy/router changes.
4. **Phase 4.5:** implement the CPU-first embodied loop (`mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, `llama.cpp`) behind existing router/policy controls, including context-aware dynamic safety upgrades for sensitive screens.
5. **Phase 5.1:** integrate one persistent memory backend (`Chroma` or `Qdrant`) with explicit retention/user-control boundaries.
6. **Phase 5.2+:** ship nightly offline learning with canary promotion gates, benchmark-regression blocking, model registry rollback, and orchestration hardening when workload scale requires it.

## Strategic Reliability Pillars

- Reflection Layer (Self-Correction)
- State Verification (Trust but Verify)
- Automated Guardrail Benchmarking
- Dynamic Safety Policy (Context-Aware)
- Deterministic Dry-Run Replay

Implementation ticket pack:

- `docs/superpowers/todos/2026-04-10-phase-4-4-reliability-tickets.md`
