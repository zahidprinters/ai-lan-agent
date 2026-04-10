<!-- Keep a Changelog - https://keepachangelog.com/en/1.1.0/ -->
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Phase 4 action routing foundation with strict JSON action schema validation, allowlist-based policy checks, and audit logging
- Initial Phase 4.5 implementation slice: local reasoning facade (`core/inference/local_reasoning.py`) and runtime perception loop (`runtime/perception_loop.py`)
- Voice/STT runtime slice: offline speech listener facade (`tools/perception/audio/stt.py`), voice chat runtime entrypoint (`runtime/voice_chat_interface.py`), and launcher/script wiring (`scripts/launch.py --mode voice`, `scripts/voice_chat.py`)
- Drafted formal Phase 4.5 embodied neural agency design for llama-cpp local reasoning, embodied perception, voice, and memory integration
- Trusted ingestion pipeline for external text sources with normalization, dedupe, trust/quality scoring, merged corpus output, and JSON reporting
- Local memory layer with SQLite-backed persistence, conversation summaries, and retrieval API plus CLI utility
- Prompt-context builder that merges memory retrieval and ingested corpus snippets, exposed through policy-gated actions (`memory.search`, `context.build`)
- Hardware profiling baseline: added machine profile doc and refresh script to keep CPU-first settings aligned with actual local hardware
- Safe adapter expansion: added low-risk PC read-only actions and first Android adapter surface behind allowlist + confirmation + safe-mode gating
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

### Changed

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
