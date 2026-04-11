# AI Lan Roadmap 🧭

This document outlines the technical evolution of the **AI Lan** project, tracking milestones from initial character-level models to full agentic autonomy and cross-platform control.

---

## 🏛️ Project Phases Summary

|Phase|Milestone|Status|Strategic Focus|HW Target|
|:----|:--------|:-----|:--------------|:--------|
|**1.0**|**Foundations**|✅|Workspace setup, character tokenizer, basic training loop.|Single-core CPU|
|**1.5**|**Refinement**|✅|Run indexing, dashboard, config hardening, static analysis.|Single-core CPU|
|**2.0**|**Maturity**|✅|Bigram baseline, model factory, generation controls, transformer.|4-core CPU|
|**2.5**|**Blocks**|✅|Feed-forward blocks, residual connections, LayerNorm, full.|4-core CPU|
|**3.0**|**Scaling**|✅|BPE tokenization, KV caching, quantization, larger datasets.|8-core CPU/AVX-512|
|**4.0**|**Agency**|🛠️|ReAct loop, tool-using APIs (Internet, PC/Windows, Android).|Edge/Mobile|
|**4.5**|**Embodiment**|🛠️|Vision, speech, screen understanding, and real-time local thinking on CPU.|CPU-only Edge|
|**5.0**|**Autonomy**|⏳|Persistent Vector Memory, Recursive Self-Learning, IoT control.|Distributed|

### Phase X (Machine-Specific Execution Lanes)

Use `docs/PHASE_X_MACHINE_PLAN.md` as the operational lane map for the active i5/16 GB machine.

- Run now: `X0` to `X4` (stability, reasoning reliability, safety verification, embodied-lite, heavy-run readiness).
- Defer: `X5` and `X6` on stronger hardware (large sweeps, long-horizon benchmarks, extended concurrency, heavy promotion loops).

---

## 📚 Reference Stack and Build Order

- Phase 4 first: choose one agent framework (`Semantic Kernel`, `LangGraph`, or `LangChain`), one browser stack (`Playwright`), one search stack (`Tavily`), one OCR stack (`Tesseract`), and one Android stack (`ADB` + `scrcpy`).
- Phase 5 first: choose one memory backend (`Chroma` or `Qdrant`), one finetuning stack (`PEFT` + `LoRA` + `QLoRA` + `TRL`), one dataset pipeline (`datasets`), one orchestration layer (`Ray` or `Airflow`), and one home automation target (`Home Assistant` + `ESPHome`).
- Study `OpenHands`, `Aider`, `Continue`, and `Open Interpreter` as coding-app references before building new project-level agent UX.
- Keep [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) as the official upstream shortlist and add tests before each adoption.

### Canonical Next-Phase Execution Sequence (2026-04-05)

This sequence is the implementation order to follow one step at a time.

1. **Phase 4.1: Framework Lock + Safety Freeze**

  Lock one stack per capability (agent, browser, search, OCR, Android) from `docs/OPEN_SOURCE_REFERENCE.md`. Freeze policy defaults to safe mode, confirmation-on-write, and full audit logging. **Exit gate:** architecture decision record plus tests proving unsafe actions are blocked without confirmation.

1. **Phase 4.2: Adapter Reliability (PC + Android + Ingestion)**

  Promote safe stubs to production-safe adapters with strict allowlists and deterministic errors. Connect trusted ingestion source manifests and enforce source scoring at ingest time. **Exit gate:** integration tests for router -> policy -> adapter path and ingestion trust filtering.

  Status: completed (2026-04-10).

1. **Phase 4.3: Evaluation + Regression Control**

  Add offline eval datasets for tool selection, argument quality, and safety behavior. Add online-style telemetry checks (latency, refusal quality, action success) on real traces. **Exit gate:** benchmark harness in CI with pass/fail thresholds and regression guardrails.

  Status: completed (2026-04-11).

1. **Phase 4.4: Reliability + Verification Layer**

  Add reflection-aware retries in the ReAct controller, post-action state verification for side-effect tools, and deterministic dry-run replay as a required change-safety gate. **Exit gate:** no infinite-loop regressions in controller tests, verified state checks for selected side-effect actions, and replay parity report for policy/router changes.

1. **Phase 4.5: Embodied Runtime (CPU-first, reasoning-first order)**

  Execute this in two slices under the same router/policy layer.
  **4.5A Reasoning-first slice:** strengthen `llama.cpp`/GGUF planning quality, tool-aware prompting, and multi-step plan/reflection reliability before deeper perception expansion.
  **4.5B Perception slice:** expand `mss`/`OpenCV` + `Tesseract` + `Vosk` + `pyttsx3` embodied loop once 4.5A reasoning gates are stable.
  **Exit gate:** end-to-end embodied loop demo with bounded latency and confirmation gates preserved.

1. **Phase 5.1: Persistent Memory + Personalization**

  Select one memory backend (`Chroma` or `Qdrant`) and wire retrieval into runtime context. Add explicit user controls for preference memory and retention boundaries. **Exit gate:** deterministic retrieval tests and documented user memory controls.

1. **Phase 5.2: Offline Learning Pipeline + Model Promotion**

  Build nightly dataset builder and reward scoring from approved interaction traces. Enforce canary eval and model registry promotion/rollback gates before activation, including automated guardrail quality benchmarking against baseline prompts. **Exit gate:** nightly run artifacts and blocked promotion on failed canary metrics.

1. **Phase 5.3: Orchestration + Operations Hardening**

  Keep single-machine scheduling first; adopt `Ray` or `Airflow` only when nightly workload requires it. Add runbooks for scheduler failure, retries, audit replay, and rollback. **Exit gate:** reproducible scheduled pipeline with operator docs and failure recovery drills.

### External Validation Notes (Internet Research)

- Agent-eval best practice supports an explicit offline -> online evaluation lifecycle before broader autonomy rollout.
- Vector memory guidance supports starting with one backend and adding distributed/multitenant tuning only after stable retrieval quality.
- Orchestration guidance supports beginning with minimal local scheduling and introducing distributed components only when scale/security boundaries require it.

### Production-Grade Reliability Overlay (Strategic Pillars)

To move from basic functionality to production-grade reliability, every in-flight phase should include these pillars:

1. **Reflection Layer (Self-Correction):** ReAct agents must inspect failed observations and attempt bounded recovery strategies rather than stalling.
2. **State Verification (Trust but Verify):** Side-effect actions should include verification probes so the agent's internal state matches host/device reality.
3. **Automated Guardrail Benchmarking:** Model promotion must be blocked when standard quality and tool-selection benchmarks regress versus baseline. The current reliability slice persists per-version quality artifacts in `runs/quality/` and blocks registry activation on missing or regressed scores.
4. **Dynamic Safety Policy:** Safety level should adapt to runtime/perception context, with stronger confirmation requirements in sensitive contexts. The reliability layer now emits a `sensitive_context` signal from runtime context and applies strong-confirmation escalation for selected risky actions.
5. **Deterministic Dry-Run Replay:** Policy/router updates must be replay-validated against historical audit logs before rollout.

Technical polish for this overlay:

- **Graceful Degradation:** If local-brain runtime fails, fall back immediately to deterministic planner mode. This fallback is now implemented with debug-safe planner metadata describing the fallback reason.
- **Telemetry Sanitization:** Scrub sensitive values from trace/log artifacts before persistence.
- **Health Dashboard:** Add a system-health view for thermal pressure, RAM, and model confidence signals. This is now implemented through `/api/health` and the `/health` dashboard tab.

---

## 📅 Phase 3.0: Scaling & Efficiency (Completed)

**Objective:** Transform the model from an experimental toy into a performant CPU-first language engine.

- [x] **BPE Tokenization (Subword IQ):** Shift from character-level to subword units for higher token efficiency.
- [x] **KV Caching (5x Speedup):** Implement Key-Value caching for smoother, real-time "typing" generation.
- [x] **Dynamic Quantization (8-bit):** Shrink model weights using `torch.qint8` to reduce memory and double execution speed.
- [x] **Rich Evaluation Suite:** Implement Perplexity, BLEU, and QA benchmarks via `scripts/evaluate.py`.
- [x] **TinyStories Dataset:** Move to curated datasets like `roneneldan/TinyStories` for better logic in small models.

---

## 🔧 Post-Phase 3 Hardening (Implemented)

**Objective:** Keep the Phase 3 stack stable while making every model-facing path checkpoint-aware and compatibility-safe.

- [x] **Shared Checkpoint Loader:** Export, evaluation, generation, and training-resume paths now recover config and tokenizer metadata from the checkpoint first, with live config only as fallback.
- [x] **Quantized Inference Guardrail:** Dynamic quantized checkpoints are supported for PyTorch inference, but export utilities reject them until a dedicated export path exists.
- [x] **Run Summary Normalization:** Leaderboard and rebuild tools now normalize both legacy flat summaries and nested `metrics` / `hyperparameters` summaries.
- [x] **Legacy Index Alias:** The canonical run index is written alongside the legacy `all_index.json` alias so older workflows keep working during migration.
- [x] **Validation Hardening:** Installation checks now verify ONNX tooling and exit nonzero when required dependencies are missing.
- [x] **Offline-Learning Promotion Guardrail:** Placeholder candidate artifacts are blocked from model-registry promotion.

---

## 📅 Phase 4.0: Autonomous Agency (The Action Layer)

**Objective:** Enable the AI to leave the "chat" and interact with the physical and digital world.

**External reference guide:** use [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) as the official upstream shortlist before introducing new agent, browser, search, OCR, or Android dependencies.

- [ ] **ReAct Integration:** Modify the model architecture to support Thought -> Action -> Observation cycles.
- [ ] **Search Tools:** Create a `tools/` directory with a DuckDuckGo/Tavily search engine bridge.
- [ ] **Multi-OS Controller:**
  - **Windows & Linux:** Implement mouse, keyboard, and shell control via `pyautogui`.
  - **Android:** Implement mobile control via ADB (Android Debug Bridge).
- [ ] **Dynamic Environment Context:** Feed real-time system state (active windows, clipboard) into the model context.

### Phase 4.0 Engineering Todo List (Professional Build Path)

- [x] **Architecture Restructure Scaffold:** Added layered folders/modules (`core`, `agents`, `tools`, `memory`, `safety`, `router`, `learning`, `runtime`, `api`, `config`, `logs`) for incremental migration.
- [x] **Minimal Working Path Scaffold:** Added first runnable path for `agents/react`, `tools/system`, `memory/short_term`, `router`, `safety`, and `main.py`.
- [x] **Function Calling Schema v1:** Define strict JSON schema for `thought`, `action`, `args`, `safety_level`.
- [x] **Tool Router Core:** Implement deterministic router that validates actions before execution.
- [x] **Web Ingestion Pipeline:** Add fetch -> clean -> dedupe -> score pipeline for external text sources.
- [x] **Source Trust Scoring:** Add allowlist and per-source quality score (docs, datasets, news).
- [x] **Agent Memory Store (Foundation):** Added local memory layer (SQLite) with retrieval API and summaries.
- [x] **PC Adapter (Safe Mode Foundation):** Added safe action subset stubs: open app, type text, read clipboard.
- [x] **Android Adapter (ADB):** Implemented allowlisted actions for launch app, tap/swipe, screenshot capture, and scrcpy mirror with confirmation and policy gating.
- [x] **Perception Adapters:** Added screenshot and OCR pipeline surfaces behind policy-gated tool adapters.
- [x] **Action Confirmation Gate (Foundation):** Confirmation required on selected write-like actions.
- [x] **Audit Logging:** Persist every action request/result for reproducibility and rollback analysis.
- [x] **Policy Engine (Foundation):** Enforce deny/allow rules by tool/action and execution context.
- [x] **Evaluation Harness:** Added benchmark harness with strict thresholds for tool success rate, latency, and safety refusal quality.
- [x] **Reflection Controller:** Add bounded self-correction in ReAct loops when a tool result fails or is inconsistent.
- [x] **Action State Verification:** Add follow-up verification tools/checks for selected side-effect actions (for example app launch confirmation).
- [x] **Deterministic Replay Gate:** Require dry-run replay checks against `action_audit.jsonl` for router/policy changes.

---

## 📅 Phase 4.5: Embodied AI Interface

**Objective:** Give AI Lan eyes, ears, and speech while staying CPU-first, local-first, and safety-gated.

**External reference guide:** use [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) for the Phase 4.5 shortlist covering screen capture, OCR, offline speech, TTS, CPU LLM runtime, and voice-skill app references such as `OpenVoiceOS`.

- [ ] **Vision Loop:** Add `mss`/`OpenCV` screen capture, `Tesseract` OCR, `EasyOCR` fallback, and optional `Ultralytics` detection.
- [ ] **Voice Input:** Add `Vosk` first, then `whisper.cpp` for higher-accuracy offline transcription when CPU budget allows.
- [ ] **Voice Output:** Add `pyttsx3` as the minimum fallback, then `Coqui TTS` for higher-quality speech.
- [ ] **Local Brain Runtime (Priority First):** Add `llama.cpp` or `llama-cpp-python` for CPU-only local reasoning and tool selection.
- [ ] **Vision Loop:** Add `mss`/`OpenCV` screen capture, `Tesseract` OCR, `EasyOCR` fallback, and optional `Ultralytics` detection.
- [ ] **Voice Input:** Add `Vosk` first, then `whisper.cpp` for higher-accuracy offline transcription when CPU budget allows.
- [ ] **Voice Output:** Add `pyttsx3` as the minimum fallback, then `Coqui TTS` for higher-quality speech.
- [ ] **Realtime Loop:** Wire mic/screen input -> perception -> LLM -> tool execution -> observation -> speech output.
- [ ] **Package Boundary:** Split the future embodied layer into `perception/vision/` and `perception/audio/` while keeping `tools/perception/` as the safe facade during migration.

### Phase 4.5 Engineering Todo List (Embodied Runtime)

- [ ] **Screen Capture Service:** Low-latency screenshot capture for desktop and browser workflows.
- [ ] **OCR Service:** Extract text from screens, documents, and dialogs for context injection.
- [ ] **Mic Stream Service:** Capture audio frames for streaming speech recognition.
- [ ] **TTS Service:** Convert agent responses to spoken output with a lightweight fallback path.
- [ ] **CPU Inference Service:** Add a local LLM runner with quantized models and bounded context windows.
- [ ] **Latency Benchmarks:** Measure end-to-end response time for vision, speech, and agent loops on low-end CPUs.
- [ ] **Safety Gates:** Keep all embodied actions behind router/policy checks and explicit confirmation where needed.
- [ ] **Dynamic Context Safety:** Use perception context to automatically elevate safety levels for sensitive screens and data.
- [x] **Health Dashboard Signals:** Expose runtime health telemetry (CPU pressure, RAM headroom, confidence) for embodied operations.

### Phase 4.5A Strong Reasoning Core Standard (2026-04-10)

This is the approved design target for the reasoning-first slice before deeper perception expansion.

1. **Core Reasoning Engine (GGUF Standard)**

    - Use a production GGUF backend (`Phi-4` preferred, `Llama 3.1/4 8B` acceptable alternate).
    - Default quantization target: `Q4_K_M` for CPU-friendly quality/performance balance.
    - Runtime backend: `llama-cpp-python` embedded in-process for low overhead and token-level interception control.

1. **Resource Strategy (Smart Residency)**

    - Keep model resident in RAM by default for low-latency replies.
    - Add memory-pressure fallback that unloads the model when host RAM pressure crosses threshold.
    - Keep default thread mapping conservative and physical-core aware (for i5 baseline: `n_threads=4`).

1. **ReAct++ Logic Loop**

    - Mandatory 3-5 step plan before first action.
    - Token-stream interception: detect `Action: <tool>` while streaming and pause generation immediately to execute tools.
    - Mandatory reflection after action failure before retry to prevent repeated-loop failure patterns.

1. **Required Hardening Addenda (Not Optional)**

    - **KV cache budget/reset policy:** summarize and compact context before cache bloat degrades runtime stability.
    - **Tool risk tiers:** classify actions as `safe`, `medium`, or `dangerous` and escalate controls accordingly.
    - **Streaming-first interception:** never wait for full completion when a tool trigger is already present in token stream.
    - **Multi-model fallback path:** route to smaller/faster model under memory pressure or simple-task profile.
    - **Structured logs:** persist thought/action/error flow to dedicated agent/tool/error logs for deterministic debugging.

1. **Target Directory Structure for This Slice**

    - `core/inference/engine.py`: llama-cpp runtime wrapper.
    - `core/inference/residency.py`: memory-aware residency monitor.
    - `core/inference/context_manager.py`: sliding-window context handling.
    - `core/inference/kv_cache_manager.py`: KV-cache budgeting and reset policy.
    - `core/inference/model_router.py`: model fallback and task-class routing.
    - `agents/react/planner.py`: mandatory multi-step plan generation.
    - `agents/react/agent.py`: upgraded ReAct++ orchestration.
    - `agents/react/reflection.py`: post-failure reflection policy.
    - `agents/react/tool_executor.py`: streaming-trigger execution and risk-tier control.
    - `agents/react/prompt_library.py`: Phi-4/GGUF-optimized system prompts.

1. **Implementation Sequence (Execution Plan)**

    - **Step 1 (Foundation):** install/build `llama-cpp-python`, stage GGUF models under `models/gguf/`, ship inference manager + residency controls.
    - **Step 2 (Agent Logic):** add planning/reflection/tool-trigger streaming and bind short-term memory into GGUF context window.
    - **Step 3 (Power Features):** continue with perception and voice depth only after reasoning reliability gates pass.

---

## 📅 Phase 5.0: Self-Learning & Personalization

**Objective:** Transform AI Lan into a lifelong, self-improving digital partner.

**External reference guide:** use [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) for the Phase 5 shortlist covering memory stores, PEFT/LoRA/QLoRA, TRL, datasets, orchestration, and Home Assistant / ESPHome integration.

- [ ] **Long-Term Memory:** Integrate with local vector stores (ChromaDB/Qdrant) to recall years of interactions.
- [ ] **Recursive Fine-Tuning:** Nightly background learning mode where the AI updates its weights from newly fetched data and its own successful actions.
- [ ] **IoT & Smart Home:** Direct control of home automation (Lights, HVAC) via Home Assistant REST APIs.
- [ ] **Style Tuning:** Automatically adjust generation parameters based on user's evolving linguistic patterns.

### Phase 5.0 Engineering Todo List (Self-Learning)

- [ ] **Learning Dataset Builder:** Build nightly dataset from approved interactions and successful action traces.
- [ ] **Reward Model v1:** Score outputs/actions on usefulness, correctness, and safety.
- [ ] **Offline Fine-Tune Job:** Add scheduled local fine-tuning pipeline with checkpoint gating.
- [ ] **Canary Evaluation:** Require benchmark pass before promoting nightly model to active use.
- [ ] **Guardrail Benchmark Suite:** Run fixed quality/tool-selection prompt sets and block promotion on regression.
- [ ] **Model Registry:** Add semantic versioning and rollback metadata for each promoted model.
- [ ] **User Preference Memory:** Persist personalized style/task preferences with explicit opt-in controls.
- [ ] **Hardware Control Expansion:** Add camera/mic/speaker/screen modules behind strict permissions.
- [ ] **Resource Manager:** Add CPU/RAM guardrails for background learning on low-end systems.

---

## Last Updated

2026-04-10
