# AI Context Guide

This file is a handoff brief for contributors and coding agents working in AI Lan.

## Read First

1. `README.md`
2. `ROADMAP.md`
3. `CHANGELOG.md`
4. `docs/PROJECT_STATUS.md`
5. `docs/ARCHITECTURE.md`
6. `docs/CONFIGURATION.md`
7. `docs/API_REFERENCE.md`
8. `docs/TESTING_GUIDELINES.md`
9. `docs/PROJECT_STRUCTURE.md`
10. `docs/OPEN_SOURCE_REFERENCE.md`

## Engineering Rules

- Keep the project Windows-first and CPU-friendly.
- Use `.venv` for all Python commands.
- Keep runtime artifacts in `temp/` and model/run artifacts in `models/` and `runs/`.
- Keep unit tests passing before and after changes.
- Update documentation in the same change when behavior/config/workflow changes.
- Prefer small, test-backed iterations over large unverified rewrites.
- Treat checkpoint metadata as the source of truth for export, evaluation, generation, and training-resume paths.
- Normalize run summaries before displaying them or rebuilding run indexes.

## Current Product Direction

AI Lan is evolving from a local text model toolkit into a safe, tool-using AI agent with:

- internet-assisted retrieval and data ingestion,
- local memory and personalization,
- controlled device actions (PC and Android),
- staged self-learning workflows with evaluation gates.
- Checkpoint-aware model loading and run-report compatibility across legacy and new summary schemas.
- Offline-learning promotion that is gated to real candidate models and rejects placeholder artifacts.

The repository now includes a layered architecture scaffold (`core/`, `agents/`, `tools/`, `memory/`, `safety/`, `router/`, `learning/`, `runtime/`, `api/`) and should be migrated incrementally without breaking current stable paths.
The next major addition is embodied AI: CPU-first screen capture, OCR, offline speech recognition, offline speech output, and local reasoning.
If you need a real skills/app reference for voice commands and plugin packaging, study `OpenVoiceOS`.

When evaluating upstream code, prefer official repos and docs from `docs/OPEN_SOURCE_REFERENCE.md`, then wrap the selected dependency behind the local facades instead of importing framework internals directly into the runtime.
Keep Phase 4 and Phase 5 intake narrow: one framework per capability, tests first, and only the shortest useful stack for the current milestone.

## Immediate Next Build Sequence

1. **Phase 4.1:** lock one stack per capability from `docs/OPEN_SOURCE_REFERENCE.md` and keep policy defaults in safe mode.
2. **Phase 4.2:** expand PC/Android adapters and ingestion connectors with strict allowlists and deterministic failures.
3. **Phase 4.3:** add integration + benchmark gates (tool success, refusal quality, latency) and enforce thresholds.
4. **Phase 4.5:** build the minimum embodied CPU stack (`mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, `llama.cpp`) behind local facades and safety checks.
5. **Phase 5.1:** integrate one persistent memory backend and verify retrieval quality under tests.
6. **Phase 5.2+:** run offline learning with model-registry promotion/rollback gates, then add orchestration only when scale requires it.

## Safety & Control Requirements

- High-risk actions require explicit confirmation.
- Every tool call must be logged with inputs, result, and status.
- Enforce allowlist/denylist policy at execution time.
- Keep all actions reversible where feasible.

## Long-Term Vision

Build a self-learning local AI that can reason, retrieve information, and safely control devices while remaining resource-efficient and auditable.
