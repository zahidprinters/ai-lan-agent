# AI Lan: AI-Agentic Workflow & Development Guidelines 🤖

This document provides a comprehensive roadmap, rule-set, and stylistic guide for AI agents working in this project.

---

## 🏗️ Project Philosophy

AI Lan is a **Windows-first, CPU-optimized, and agent-centric** workspace.
- **Independence:** The project should be fully runnable on a standard laptop (i5, 16GB RAM) without external GPU dependence.
- **Transparency:** Use `sentinel` (@debug_utils) for everything. Do not guess; trace.
- **Safety First:** Actions that modify the system (PC, Android, Smart Home) **must** go through the `Action Router` with a `Policy Decision`.

---

## 🛠️ Developer Rules (Agentic Directive)

### 1. Codestyle & Tooling
- **Language:** Python 3.11+.
- **Standard Library:** Prefer standard library over heavy external dependencies (e.g., `subprocess` over complex wrappers).
- **Type Hints:** Mandatory. Every function must have type hints for input and output.
- **Decorators:** Every major logic function should be decorated with `@sentinel`.
- **Formatting:** Adhere to `.editorconfig`. Use `black` and `isort` before committing.

### 2. The Sentinel Mandate
- **Trace Mode (`AI_LAN_TRACE=1`):** Use this for reproducing logic bugs.
- **Profile Mode (`AI_LAN_PROFILE=1`):** Use this for performance audits.
- **Log Files:** Redirect all sentinel output to `AI_LAN_DEBUG_LOGFILE` during long-running training.

### 3. File Hygiene
- **Temporary Data:** Must be stored in `temp/` (ensure `TEMP_DIR` is initialized using `ensure_project_temp`).
- **Data/Artifacts:** Never commit `.pt` models (check `.gitignore`).
- **Dead Code:** Delete scratchpads immediately.

### Checkpoint & Artifact Rules
- Use the shared checkpoint helpers in `training/checkpoints.py` for any export, evaluation, generation, resume, or run-reporting path.
- Treat checkpoint metadata as the source of truth; live config is a fallback only when the checkpoint does not carry enough information.
- Quantized checkpoints are inference-only until a dedicated export path is added. Do not route them through generic export tools.
- Run summaries may arrive in legacy flat form or nested `metrics` / `hyperparameters` form, so normalize before displaying or rebuilding indexes.
- Never promote placeholder artifacts in offline-learning or model-registry workflows.

### 4. External Code Intake
- Use [OPEN_SOURCE_REFERENCE.md](OPEN_SOURCE_REFERENCE.md) as the curated shortlist before adopting any new upstream project.
- Prefer official upstream repos and documentation over blog posts, forks, or random snippets.
- Check the upstream license, maintenance activity, and install footprint before wiring the dependency into the runtime.
- Keep external integrations behind local facades in `core/`, `agents/`, `tools/`, `memory/`, or `learning/`.
- Add or update tests before promoting an external dependency into the live path.
- Phase 4 should stay limited to one agent framework, one browser stack, one search stack, one OCR stack, and one Android stack.
- Phase 4.5 should stay limited to `mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, and `llama.cpp` until the CPU-only embodied loop is stable.
- Study `OpenVoiceOS` if you need a real skills/app reference for voice commands and plugin packaging.
- Phase 5 should stay limited to one memory backend, one finetuning stack, one dataset pipeline, one orchestration layer, and one home automation target.
- Study coding-app references such as `OpenHands`, `Aider`, `Continue`, `Open Interpreter`, and `OpenCodeInterpreter` before building new internal UX.

---

## 🔄 Interaction & ReAct Guidelines

When implementing new tools or actions:
1.  **Define Schema:** Add it to `router/schema.py`.
2.  **Define Policy:** Add it to `safety/policy_engine.py` (identify if it needs confirmation).
3.  **Implement Stub:** Write a safe, read-only stub in `tools/` first.
4.  **Register:** Add to `TOOL_REGISTRY` in `router/dispatch_core.py`.
5.  **Adopt Upstream Carefully:** Match the selected capability against [OPEN_SOURCE_REFERENCE.md](OPEN_SOURCE_REFERENCE.md), then integrate one upstream project at a time behind the local interface.

---

## 🎯 Project Milestones (The "Goal")

1.  **Phase 3.5 (Efficiency):** Reach 30 tokens/sec on Intel UHD 620.
2.  **Phase 4.0 (Action):** Full "Wait for Confirmation" dashboard for PC and Android control.
3.  **Phase 4.5 (Embodiment):** Add screen, camera, mic, and speech loops that work on CPU-only hardware.
4.  **Phase 5.0 (Autonomy):** Long-term memory store (retrieve last year's chat history in 50ms).

---

## 📝 Commit Conventions

Use the following prefixes for all commits:
- `feat:` New features or tools.
- `fix:` Bug fixes or policy adjustments.
- `refactor:` Cleaning up code or renaming variables.
- `docs:` Documentation updates.
- `perf:` Performance optimizations (quantization, compilation).

---

## Last Updated

2026-04-05
