# Ecosystem Phase Re-Audit (2026-04-13)

## Objective

Shift AI Lan from a single-host assistant model to a full ecosystem architecture:

- one reasoning and safety core,
- many clients (CLI, Web, API, voice, mobile),
- many control planes (PC, Android, Home/IoT),
- shared memory, policy, audit, and health telemetry.

## Current Delivery Audit

| Capability | Status | Delivered Now | Still Required |
| :--- | :--- | :--- | :--- |
| Reasoning + safety kernel | done | Schema validation, policy gating, confirmation flow, audit replay, health telemetry | Longer-horizon failure-mode regression suites |
| PC + Android adapters | done | Allowlisted, policy-gated adapter surfaces with deterministic timeout behavior | Broader side-effect verification coverage |
| Internet intelligence loop | in progress | Trusted ingestion, scoring, dedupe, context assembly | Freshness weighting, drift detection, scheduler profiles |
| Memory + personalization | in progress | SQLite and optional Chroma retrieval path | Retrieval quality tuning and retention automation |
| Voice/perception runtime | in progress | Voice chat + bounded perception + OCR backend controls | Satellite architecture, wake-word/device lifecycle hardening |
| Multi-client surfaces | done | Unified launcher for CLI/Web/API with shared runtime model | Mobile-first companion flow and device federation |
| Home/IoT integration | not started | Planned only in roadmap and docs | Home Assistant + ESPHome adapter plane with strict policy packs |
| Guarded self-evolution | not started | Concept and guardrails documented | Proposal-only patch loop with mandatory CI/replay/benchmark gate |

## Rearranged Development Phases

1. Phase 1.0 Safety and Governance Foundation (done)
2. Phase 1.1 Verified Adapter Reliability (done)
3. Phase 2.0 Reasoning and Perception Core (done)
4. Phase 2.1 Reliability and Evaluation Gates (done)
5. Phase 3.0 Knowledge Mesh (in progress)
6. Phase 3.1 Memory Persona Layer (in progress)
7. Phase 4.0 Ecosystem Client Surfaces (in progress)
8. Phase 4.1 Home and IoT Orchestration (next)
9. Phase 5.0 Guarded Self-Evolution (last)

Execution rule: complete 3.0 before 3.1, complete 3.1 before 4.0, complete 4.0 before 4.1, and complete 4.1 before 5.0.

## Ecosystem Signals from Internet Research

These references support ecosystem-first architecture decisions:

- Home Assistant Assist: local-first and cloud-optional voice path, Android wake-word support, ESPHome voice satellites.
- OpenVoiceOS: multi-platform voice-assistant packaging model for embedded/headless/screen devices.
- Open Interpreter: local execution model with explicit human approval and server mode for multi-surface orchestration.
- Semantic Kernel and LangGraph: mature patterns for multi-agent orchestration, plugin contracts, memory, streaming, and human-in-the-loop controls.

## Immediate Build Queue

1. 3.0.1 Add ingestion scheduler profiles and source freshness scoring.
2. 3.0.2 Add source drift reports into dashboard/API health payloads.
3. 3.1.1 Add retrieval quality benchmark fixtures for long-term memory.
4. 3.1.2 Add deterministic memory retention jobs and operator controls.
5. 4.0.1 Define companion/mobile contract and auth/session boundaries.
6. 4.0.2 Add voice satellite protocol and device enrollment model.
7. 4.1.1 Implement Home Assistant read-only adapter first (entity discovery/status).
8. 4.1.2 Add confirmation-gated write actions with strict policy tiers.

## Non-Negotiable Gates

- No side-effect execution path without policy + confirmation support.
- No planner/runtime changes merged without replay and benchmark checks.
- No autonomous patch apply path before proposal-only mode proves stable.
