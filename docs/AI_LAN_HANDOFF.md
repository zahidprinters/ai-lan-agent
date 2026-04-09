# AI Lan Handoff (2026-04-05)

## Carry-forward state

- Phase 3 remains stabilized: training, inference, tokenizers, checkpoints, ONNX export, quantization, and run indexing are in place.
- Shared checkpoint handling is now the source of truth for export, evaluation, generation, and training resume, so config/tokenizer metadata should come from the checkpoint first.
- Run indexes are normalized across legacy flat and nested summary schemas, and both the canonical run index and the legacy `all_index.json` alias are kept in sync.
- Dynamic quantized checkpoints are supported for PyTorch inference, but generic export paths now reject them until a dedicated export route exists.
- Current project direction across README, ROADMAP, AI context, and project status is consistent: AI Lan is moving from local LM tooling into a safe, tool-using agent.
- The next build slice is embodied AI: screen capture, OCR, speech-to-text, text-to-speech, and local CPU reasoning.
- Phase 4 foundation now includes strict action schema parsing, policy-gated routing, JSONL audit logging, and a first trusted ingestion pipeline.
- Memory layer foundation is now added with local SQLite persistence, conversation summaries, and ranked retrieval.
- Context assembly is now connected: prompt context can be built from memory hits + ingestion corpus snippets via policy-gated actions.
- Machine hardware baseline is now documented and scriptable for this small laptop setup (CPU-first, no discrete GPU).
- Known intentional Phase 4 stubs remain:
  - actions/react_loop.py
  - tools/web_search.py
  - tools/pc_control.py
- Sentinel observability remains part of the documented architecture and developer workflow.
- The documented testing baseline is still:
  - python -m pytest tests -q --disable-warnings --ignore=tests/integration

## What was reviewed for this handoff

- Read all markdown files in the workspace, including root docs, docs/, and docs/superpowers/ plans/specs.
- Confirmed consistent themes across the documentation:
  - Windows-first and CPU-friendly operation
  - Always use .venv
  - Keep temp artifacts inside temp/
  - Keep documentation updated with behavior changes
  - Start Phase 4 with deterministic routing and safety before broader autonomy

## Important current context

- README and PROJECT_STATUS describe the repository as a modular training and inference workspace with Phase 4 agency work next.
- docs/OPEN_SOURCE_REFERENCE.md is now the canonical upstream intake list with current repo URLs and short usage notes for each phase.
- ROADMAP prioritizes Function Calling Schema, Tool Router, embodied perception, web ingestion, memory, safe PC/Android adapters, policy engine, audit logging, and evaluation harness.
- The shared checkpoint helpers in `training/checkpoints.py` now own config recovery, quantized inference loading, and run-summary normalization.
- AI_CONTEXT now states the immediate build sequence:
  1. Build the minimum embodied CPU stack (`mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, `llama.cpp`) behind local facades and safety checks
  2. Select one agent framework, one browser automation stack, one search stack, and one OCR stack from docs/OPEN_SOURCE_REFERENCE.md, then expand safe action adapters for PC and Android
  3. Add integration tests for router + context builder + persisted artifacts
  4. Connect curated trusted source manifests to ingestion workflows
  5. Add benchmark harness for action success, safety, and latency
  6. Start offline learning pipeline and model registry/rollback scaffolding with the Phase 5 stack (`PEFT`, `LoRA`, `QLoRA`, `TRL`, `datasets`)
- TESTING_GUIDELINES and docs in general reinforce that .venv must stay active for all Python commands.

## My strategic suggestions (high impact)

- Keep Phase 4 and Phase 5 intake narrow: one framework per capability, tests first, and the smallest stack that solves the current milestone.
- Build the embodied CPU loop before expanding autonomy so the agent can see, hear, and speak in a controlled way.
- Build Function Calling Schema first (strict JSON action format + validation).
- Add Safety Policy Engine before real device control (allowlist, confirmation for risky actions, full audit logs).
- Build Retrieval/Data pipeline before nightly self-learning (fetch, clean, dedupe, trust scoring).
- Start PC/Android control with safe read-only and low-risk actions first.
- Add evaluation gates for action success, refusal quality, and latency before autonomous execution.

## Next todo list (recommended implementation order)

1. **Phase 4.1:** lock one stack per capability and finalize safe defaults (confirmation-on-write, audit-on-all-actions).
2. **Phase 4.2:** harden PC/Android adapters and ingestion connectors with strict allowlists and deterministic behavior.
3. **Phase 4.3:** add benchmark/eval gates (offline datasets + online-style telemetry checks) and enforce thresholds.
4. **Phase 4.5:** implement CPU-first embodied loop (`mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, `llama.cpp`).
5. **Phase 5.1:** integrate one persistent memory backend (`Chroma` or `Qdrant`) with retrieval-quality tests.
6. **Phase 5.2:** build nightly offline learning + reward/canary promotion gates.
7. **Phase 5.3:** add orchestration hardening (`Ray` or `Airflow`) only when local scheduling limits are reached.

## Tomorrow starting point

1. Expand safe PC adapter coverage one low-risk action at a time.
2. Add a first Android adapter surface behind strict allowlist policy.
3. Keep policy checks and audit logging in front of every new tool surface.
4. Add focused tests for safe adapter execution and policy enforcement.
5. Add integration tests for router + context builder with persisted memory and merged corpus artifacts.

## Completed today

- Implemented strict Phase 4 action schema parsing, deterministic routing, policy gating, and JSONL audit logging.
- Added safe PC stubs for `open_app` and `read_clipboard` alongside confirmation-gated typing.
- Implemented trusted ingestion pipeline foundation:
  - source loading from JSON config
  - `file`, `inline`, and `http` source support
  - normalization, document dedupe, line dedupe, trust/quality scoring
  - merged corpus output and JSON report artifacts
- Focused verification passed:
  - python -m pytest tests/test_action_router.py tests/test_temp_policy.py -q --disable-warnings
  - python -m pytest tests/test_ingestion_pipeline.py tests/test_clean_dataset.py -q --disable-warnings
- Implemented memory layer foundation:
  - local SQLite-backed memory store under temp/memory/
  - summary generation for stored entries
  - conversation summary persistence API
  - deterministic ranked retrieval API
  - CLI utility for add/search/recent workflows
- Additional focused verification passed:
  - python -m pytest tests/test_memory_store.py tests/test_action_router.py tests/test_ingestion_pipeline.py tests/test_clean_dataset.py tests/test_temp_policy.py -q --disable-warnings
- Connected retrieval into policy-gated actions and prompt-context assembly:
  - added `memory.search` router action
  - added `context.build` router action
  - added prompt-context builder combining memory and corpus snippets
- Additional focused verification passed:
  - python -m pytest tests/test_context_builder.py tests/test_action_router.py tests/test_memory_store.py tests/test_ingestion_pipeline.py tests/test_clean_dataset.py tests/test_temp_policy.py -q --disable-warnings
- Resumed after workstation restart with additional safe adapter coverage:
  - added `pc.list_workspace_files` (read-only, workspace-scoped listing with traversal blocking)
  - wired routing and policy allowlist support for the new low-risk action
  - added router tests for normal listing and path traversal blocking
- Hardened Android adapter behavior on machines without ADB:
  - `android.list_devices` now returns `adb_unavailable` instead of raising
  - other adb-backed Android actions now return safe `failed` payloads when adb is missing
- Additional focused verification passed:
  - python -m pytest tests/test_action_router.py tests/test_temp_policy.py -q --disable-warnings
- Added non-destructive architecture restructure scaffold aligned to Phase 4/5 template:
  - created layered directories and starter modules for `core`, `agents`, `memory`, `safety`, `router`, `learning`, `runtime`, `api`, and `config`
  - added `main.py` and starter scripts for `scripts/train.py` and `scripts/benchmark.py`
  - added architecture guide: `docs/PROJECT_STRUCTURE.md`
- Completed next-step migration wiring for the layered scaffold:
  - implemented stateful runtime in `agents/react/agent.py` with `ReactAgent` and `run_react_step`
  - upgraded `memory/short_term/buffer.py` to role-tagged message storage and context rendering
  - added dispatch helpers in `router/router.py` and policy helpers in `safety/policy_engine.py`
  - upgraded `runtime/context.py` to assemble short-term + retrieved context together
  - upgraded `tools/web/search.py` with `WebSearchTool` abstraction and helper runner
  - added test coverage in `tests/test_layered_modules.py`
- Focused verification passed:
  - python -m pytest tests/test_layered_modules.py tests/test_action_router.py tests/test_temp_policy.py -q --disable-warnings
- Migrated one production execution flow to layered-first routing with fallback:
  - `main.py` now executes through `ReactAgent` instead of direct legacy executor
  - `ReactAgent.run_step` now uses `router.parse_and_dispatch` first
  - `router/router.py` now does layered-first handling for selected actions (`web.search`, `pc.read_clipboard`, `pc.list_workspace_files`)
  - layered-first path explicitly passes through safety policy checks before tool execution
  - if layered handling fails or action is not layered, router falls back to legacy `actions.router.dispatch_agent_action`
- Hardened checkpoint/reporting flows:
  - export, evaluation, generation, and training-resume paths now recover config/tokenizer metadata from the checkpoint first
  - run summaries are normalized before leaderboard display and index rebuilds
  - placeholder candidate artifacts are blocked from offline-learning promotion
  - ONNX installation validation now checks the actual export/runtime packages and exits nonzero when they are missing
- Additional verification passed:
  - python main.py

## Important notes

- Keep .venv active for all commands.
- Keep project Windows-first and CPU-friendly.
- Keep temporary artifacts inside temp/ only.
- Keep docs updated alongside code changes.
- Refresh machine hardware snapshot when environment changes: `powershell -ExecutionPolicy Bypass -File scripts/hardware_profile.ps1`
