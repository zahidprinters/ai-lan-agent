<!-- Keep a Changelog - https://keepachangelog.com/en/1.1.0/ -->
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Added `docs/SECURITY_POLICY.md` documenting safe mode, confirmation gates, audit logging, and local machine protection rules for tool use
- Added `scripts/install_system_deps.ps1` to install and verify Tesseract OCR, Android Platform Tools, and scrcpy on Windows
- One-command resource audit workflow: `scripts/regenerate_resource_inventory.py` plus `scripts/audit_resources.ps1` now regenerate the local resource inventory and Python package snapshot automatically
- Phase 4 action routing foundation with strict JSON action schema validation, allowlist-based policy checks, and audit logging
- Initial Phase 4.5 implementation slice: local reasoning facade (`core/inference/local_reasoning.py`) and runtime perception loop (`runtime/perception_loop.py`)
- Voice/STT runtime slice: offline speech listener facade (`tools/perception/audio/stt.py`), voice chat runtime entrypoint (`runtime/voice_chat_interface.py`), and launcher/script wiring (`scripts/launch.py --mode voice`, `scripts/voice_chat.py`)
- Memory backend slice: optional ChromaDB facade (`memory/long_term/chroma_store.py`) with runtime retrieval wiring through chat/context/API paths and automatic fallback to local vector scoring
- Bounded neural ReAct loop in chat/runtime: the local planner can now execute a low-risk action, observe the result, and continue to a final reply with step-budget and repeated-action suppression
- Model-facing tool schema layer: the planner prompt now receives structured tool descriptions, arg contracts, confirmation hints, and risk labels derived from the router registry
- Live perception context wiring: chat/runtime sessions can now keep the latest OCR perception snapshot in session state and inject it into assembled planner context when perception is enabled
- Runtime cleanup hardening: CLI and voice chat now close session resources on exit, and dashboard/API state now exposes the current live perception snapshot consistently
- Runtime performance optimization: adaptive perception backoff for unchanged screens, bounded runtime-context section sizes, and dashboard context reuse to reduce repeated high-cost context assembly
- Drafted formal Phase 4.5 embodied neural agency design for llama-cpp local reasoning, embodied perception, voice, and memory integration
- Trusted ingestion pipeline for external text sources with normalization, dedupe, trust/quality scoring, merged corpus output, and JSON reporting
- Local memory layer with SQLite-backed persistence, conversation summaries, and retrieval API plus CLI utility
- Prompt-context builder that merges memory retrieval and ingested corpus snippets, exposed through policy-gated actions (`memory.search`, `context.build`)
- Hardware profiling baseline: added machine profile doc and refresh script to keep CPU-first settings aligned with actual local hardware
- Safe adapter expansion: added low-risk PC read-only actions and first Android adapter surface behind allowlist + confirmation + safe-mode gating
- Phase 4.2 Android adapter hardening: app launches now require explicit package allowlists, side-effect actions can be restricted to known device IDs, and Android screenshots are constrained to `temp/`
- Added benchmark harness for tool success/safety/latency metrics and scaffolded offline learning + model registry/rollback workflow
- Focused tests for action schema parsing, router dispatch, policy rejection, and ReAct payload execution
- Unit tests for experiment profile selection and environment variable override in config
- Unit test for top-p (nucleus) sampling in inference
- Test for dataset cleaning script (removes duplicates and empty lines)
- Enforced train_ratio < 1.0 in config validation
- All chat models (ELIZA, Local ML AI, Smart AI) now support saving chat transcripts with `/save` (saved in `runs/`)
- Improved CLI prompt formatting for all chat models
- Added dataset cleaning script (`scripts/clean_dataset.py`) and PowerShell wrapper (`scripts/clean_dataset.ps1`)
- Integrated dataset cleaning as a menu/dashboard action (`clean_dataset`) in `main.ps1`
- Cleaning removes empty lines and duplicate lines, outputs `input_cleaned.txt`
- Optional Phase 4 setup commands and verification flow in docs for Playwright + Tavily + Tesseract + ADB/scrcpy on Windows
- Policy-config tests and debug-sanitization tests covering YAML policy loading, fallback behavior, and masked sentinel trace output
- Added audit replay dry-run workflow (`scripts/replay_audit.py`) to simulate historical action requests against current router/policy behavior without executing side effects
- Added focused tests for local-brain backend fallback/selection and perception loop snapshot lifecycle
- Added voice runtime tests for STT fallback path and voice CLI loop behavior
- RL-01 reliability slice: bounded reflection retries in the ReAct runtime with repeated-action suppression and explicit skip reasons when recovery or retry budget is exhausted
- RL-02 reliability slice: selected side-effect router actions now include verification metadata (`verified`, `not_verified`, `verification_failed`) in their observation payloads
- RL-03 reliability slice: `scripts/benchmark_quality.py` now writes machine-readable quality artifacts and `scripts/model_registry.py activate` blocks model promotion on missing, below-threshold, or below-baseline benchmark scores
- RL-04 reliability slice: runtime context now emits `sensitive_context`, and policy evaluation escalates selected risky actions to strong confirmation in sensitive contexts
- RL-05 reliability slice: audit replay now emits deterministic `matched` / `diverged` / `skipped` summaries, supports strict nonzero exits, and is wired into CI for router/policy changes
- RL-06 reliability slice: local-brain (`llama_cpp`) planning now degrades immediately to classic generation on runtime/model failures and includes debug-safe fallback reason metadata
- RL-07 reliability slice: dashboard/API now provide health telemetry (`/api/health` and `/health`) including CPU pressure proxy, RAM usage snapshot, and model confidence summary

### Changed

- Default environment setup no longer installs experiment tracking packages automatically; `wandb` and `mlflow` are now opt-in via `python -m pip install .[experiment]` so the active `.venv` can stay conflict-free
- Updated base packaging pin to `packaging==24.2` to align with `pyproject-api==1.7.1`
- Refreshed project documentation for accuracy and consistency: `README.md`, `docs/API_REFERENCE.md`, `docs/PROJECT_STATUS.md`, and `docs/ARCHITECTURE.md`
- Expanded the curated upstream reference and roadmap guidance across `docs/OPEN_SOURCE_REFERENCE.md`, `ROADMAP.md`, `project_plan.md`, `docs/AI_GUIDELINES.md`, `docs/AI_CONTEXT.md`, `docs/AI_LAN_HANDOFF.md`, `docs/USER_GUIDE.md`, `docs/CONTRIBUTING.md`, and `docs/PROJECT_STRUCTURE.md`
- Added embodied AI guidance for CPU-first vision, speech, and local reasoning across the roadmap and docs
- Standardized a canonical 2026-04-05 implementation sequence across roadmap/status/handoff docs (Phase 4.1 framework lock -> 4.2 adapter hardening -> 4.3 eval gates -> 4.5 embodied loop -> 5.x memory/learning/orchestration), including explicit entry/exit gates for each stage
- Reorganized dependency guidance to distinguish runtime requirements from optional experiment tracking dependencies
- Clarified test observability defaults (debug on by default, trace/profile opt-in)
- Pinned optional Phase 4 Python dependencies in `requirements.txt` and added `project.optional-dependencies.phase4` in `pyproject.toml`
- Updated `README.md`, `docs/USER_GUIDE.md`, `docs/CONFIGURATION.md`, and `docs/OPEN_SOURCE_REFERENCE.md` with Phase 4 install commands and `TAVILY_API_KEY` configuration guidance
- `safety/policy_engine.py` now loads `allow_actions`, `deny_actions`, and `require_confirmation` from `config/policies.yaml` with safe default fallbacks
- `training/config.py` now exposes centralized `ProjectConfig.debug` settings (`DebugSettings`) while keeping compatibility fields (`debug_trace`, `debug_profile`)
- `debug_utils.py` now masks sensitive trace variable names/content before logging line-level sentinel traces
- Updated `docs/PROJECT_STATUS.md` to reflect that Phase 4.1 safety freeze is effectively implemented
- `agents/react/controller.py` now supports `AI_LAN_REASONING_BACKEND=llama_cpp` with deterministic fallback to classic generation when local-brain runtime/model is unavailable
- `training/config.py` now includes typed Phase 4.5 settings for local reasoning backend, llama-cpp runtime tuning, perception loop controls, and memory backend pathing
- Updated `docs/CONFIGURATION.md` with Phase 4.5 environment variable reference for local brain and embodied runtime controls
- Updated `README.md` and `docs/USER_GUIDE.md` with voice-mode launch and STT/TTS setup guidance

### Fixed

- Removed unused imports and obsolete compatibility aliases from source files
- Improved checkpoint config reconstruction compatibility by ignoring unknown legacy keys
- Cleaned temporary/cache artifacts and duplicate transient files from the workspace

## [0.2.0] - 2026-03-25

### Major

- Architectural Pivot: Transitioned from CharMLP to StackedTransformer with GELU, LayerNorm, and Residuals
- Vision Pivot: Integrated the Master Vision and 4-Stage Evolution Plan
- Refactored folder structure to support evolution_ai/ and modular design
- Integrated BPE tokenizer and KV caching logic
- Added config-driven model scaling (n_layer, n_head, hidden_size)

### Enhancements

- Improved documentation alignment across README, ROADMAP, and docs/
- Added experiment profiles for transformer scaling
- Improved training pipeline for flexibility and reproducibility

### Fixes

- Synchronized documentation and code for new architecture

## [0.1.1] - 2026-03-25

### Added (0.1.1)

- Experiment profile support: select `debug`, `baseline`, or `transformer_small` via `AI_LAN_EXP_PROFILE` to quickly set up common experiment configs.
- Profiled config values can be overridden by environment variables for flexibility.

## [0.1.0] - 2026-03-25

### Added (0.1.0)

- Implemented shallow transformer model (single-head self-attention, positional encoding, CPU-friendly)
- Registered transformer model in the model factory for easy selection and experimentation
- Updated documentation to describe transformer usage and testing
- `docs/` folder for secondary project documentation
- Shared PowerShell helper module `scripts/utils.ps1`
- Centralized Python config in `training/config.py`
- `.editorconfig`
- `pyproject.toml` for pytest, black, and mypy settings
- `dev-requirements.txt` for reproducible developer tooling installs
- `ROADMAP.md` for long-term project planning
- `docs/PHASE_2_DESIGN.md` for the approved Phase 2 technical direction

### Changed (0.1.0)

- removed redundant PowerShell alias entry files and kept `main.ps1` as the only top-level entry point
- removed redundant `main.py` bootstrap script
- removed duplicate `models/training_samples.txt` artifact and kept versioned samples under `runs/`
- merged command reference into `README.md`
- removed the separate file index document to reduce documentation overlap
- improved CLI headers and step output in PowerShell scripts
- added training configuration summary and simple ETA output in the training module
- improved generation output formatting with a clearer seed and output separator
- validated key numeric environment overrides before runtime so invalid settings fail fast with clear errors
- removed unused runtime dependencies from `requirements.txt`
- updated setup and README so the development toolchain is installed from `dev-requirements.txt`
- updated metadata and handoff docs to reflect the approved Phase 2.0 roadmap and transformer-foundation agenda

### Fixed (0.1.0)

- added package markers so stricter static analysis tools resolve `training/`, `tokenizer/`, and `tests/` consistently
- added explicit file existence checks for training data and generation assets to avoid confusing downstream failures

### Verified

- dashboard works
- unit tests pass
- integration tests pass
- docs links match the simplified structure
- repo is ready to close Phase 1.5 and begin the next milestone
