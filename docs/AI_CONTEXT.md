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

Canonical ecosystem re-audit and phase ordering reference: `docs/plans/ECOSYSTEM_PHASE_REAUDIT_2026-04-13.md`.

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
The formal design starting point for this slice is `docs/superpowers/specs/2026-04-10-embodied-neural-agency-design.md`.

When evaluating upstream code, prefer official repos and docs from `docs/OPEN_SOURCE_REFERENCE.md`, then wrap the selected dependency behind the local facades instead of importing framework internals directly into the runtime.
Keep Phase 4 and Phase 5 intake narrow: one framework per capability, tests first, and only the shortest useful stack for the current milestone.

## Immediate Next Build Sequence

1. **Phase X lane enforcement (current machine):** execute only `X0` through `X4` from `docs/plans/PHASE_X_MACHINE_PLAN.md` on the active i5/16 GB host; queue heavy jobs to `X5/X6`.
2. **Phase 3.0 Knowledge Mesh (Immediate):** complete scheduler-driven ingestion, freshness/trust weighting, and source drift diagnostics.
3. **Phase 3.1 Memory Persona Layer (Immediate):** improve long-term retrieval precision and deterministic retention for personalized behavior.
4. **Phase 4.0 Ecosystem Client Surfaces (Immediate):** expand from CLI/Web/API into companion/mobile and satellite-capable control surfaces.
5. **Phase 4.1 Home/IoT Orchestration (Next):** integrate Home Assistant/ESPHome adapters behind strict policy, allowlist, and confirmation profiles.
6. **Phase 5.0 Guarded Self-Evolution (Last):** meta-agent proposes changes only; self-modification requires mandatory tests/replay/benchmark gates.

Execution rule for this cycle: prefer brain-first upgrades (reasoning/planning quality) before eye/ear expansion (vision/audio perception depth).

## Ecosystem Direction Lock (2026-04-13)

AI Lan now targets a full assistant ecosystem, not only a PC assistant:

- one safe reasoning core,
- multiple client surfaces (CLI/Web/API/voice/mobile),
- multiple controlled action planes (PC/Android/Home/IoT),
- shared memory/policy/audit across all surfaces.

External architecture signals used to shape this direction:

- Home Assistant Assist for local-first + cloud-optional voice and home automations,
- OpenVoiceOS for multi-device voice satellite ecosystem patterns,
- Open Interpreter for local execution with explicit human approval and server mode,
- Semantic Kernel/LangGraph for multi-agent orchestration, tool contracts, memory, and HITL control.

## Reliability Pillars (Production-Grade Overlay)

- Reflection-based self-correction: avoid stalled loops after tool failures.
- State verification: confirm side-effect outcomes with read-only probes.
- Guardrail benchmarking: block candidate model promotion on quality regression.
- Dynamic policy: elevate safety requirements using runtime/perception context.
- Deterministic dry-run replay: validate new policy/router behavior against historical logs before rollout.

Current Phase 4.4 status: reflection retries, post-action verification, quality benchmark gating for model promotion, dynamic context-aware safety escalation, graceful local-brain degradation, health dashboard telemetry, and strict deterministic replay gating are now implemented as the reliability foundation.

Phase 4.5A direction lock (2026-04-10) outcome: achieved on 2026-04-11. Phase 4.5B is now also complete; retain the same reasoning/safety regression gates as mandatory pre-merge checks while advancing Phase 5 work.

## Safety & Control Requirements

- High-risk actions require explicit confirmation.
- Every tool call must be logged with inputs, result, and status.
- Enforce allowlist/denylist policy at execution time.
- Keep all actions reversible where feasible.

## Long-Term Vision

Build a self-learning local AI that can reason, retrieve information, and safely control devices while remaining resource-efficient and auditable.

