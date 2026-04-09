# AI Lan: Master Project Plan 🛣️

This document serves as the single source of truth for all current and future work in the AI Lan ecosystem. It provides the high-level roadmap and detailed implementation status for each phase.

---

## 🏛️ Project Vision

To build a high-fidelity, local-first language model that transitions from passive "chat" to active "agency," enabling autonomous control of Windows, Linux, and Android environments on consumer-grade CPU hardware.

---

## 📅 Roadmap & Milestones

### ✅ Phase 1.0 - 2.5: Foundations & Maturity (Completed)

- [x] Character-level training loop.
- [x] Bigram baseline implementation.
- [x] **StackedTransformer-v2:** RoPE, KV Caching, Stochastic Depth.
- [x] Dashboard (`main.ps1`) and multi-run indexing.
- [x] Sentinel observability core (basic debug, variable trace, performance profiling).

### 🛠️ Phase 3.0: Scaling & Efficiency (Active)

- [x] BPE (Subword) Tokenization.
- [x] 8-bit dynamic quantization for CPUs.
- [ ] **KV Caching Optimization:** Reach 30+ tokens/sec on Intel UHD 620.
- [ ] **Data Pipeline:** Automated fetch -> clean -> dedupe pipeline for `TinyStories` and `OpenWebText`.

### 🚀 Phase 4.0: Autonomous Agency (Strategic Focus)

- [x] **Action Router Core:** Schema validation, security policy evaluation, and tool registration.
- [x] **Tool Stubs:** PC control (read-only), Android control (ADB stubs).
- [ ] **Confirmation UI:** Integrate "Wait for Approval" gates into the Dashboard for high-risk actions.
- [ ] **Web Search Tool:** Implement a functional DuckDuckGo/Tavily adapter.
- [ ] **ReAct Integration:** Refine prompt templates to enable reliable Thought -> Action -> Observation cycles.

### 👁️ Phase 4.5: Embodied AI Interface (Next Build Slice)

- [ ] **Vision Pipeline:** Add `mss`/`OpenCV` capture, `Tesseract` OCR, `EasyOCR` fallback, and optional `Ultralytics` object detection.
- [ ] **Voice Input:** Add `Vosk` first, then `whisper.cpp` for stronger offline speech recognition.
- [ ] **Voice Output:** Add `pyttsx3` as the lightweight fallback and `Coqui TTS` for higher-quality speech.
- [ ] **CPU Brain Runtime:** Add `llama.cpp` or `llama-cpp-python` for local reasoning on CPU-only hardware.
- [ ] **Realtime Loop:** Connect screen/audio perception to the agent loop and back to spoken output.

### 🧠 Phase 5.0: Autonomy & Self-Learning (Future)

- [ ] **Memory Integration:** Connect the SQLite/ChromaDB memory store to the inference loop.
- [ ] **Recursive Fine-Tuning:** Implement a background "Sleep Mode" for model self-improvement.
- [ ] **IoT Expansion:** Connect to Home Assistant for physical world interaction.

### 📚 External Reference Stack

- Official upstream shortlist: [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md)
- Phase 4 priority order: one agent framework, one browser automation stack, one search stack, one OCR stack, one Android stack, then desktop fallback tools only if needed.
- Phase 4.5 priority order: one vision stack, one speech-to-text stack, one text-to-speech stack, and one CPU LLM runtime.
- Phase 4.5 voice-skill reference: `OpenVoiceOS`.
- Phase 5 priority order: one memory backend, one finetuning stack, one dataset pipeline, one orchestration layer, and one home automation target.
- Skill/app references worth studying first: `OpenVoiceOS`, `OpenHands`, `Aider`, `Continue`, `Open Interpreter`, and `OpenCodeInterpreter`.

### ✅ Canonical Implementation Order (One Slice at a Time)

1. **4.1 Framework Lock + Safety Freeze**
   - Choose one stack per capability and lock in docs/config.
   - Keep safe mode and confirmation gates mandatory.
2. **4.2 Adapter Reliability**
   - Upgrade PC/Android/ingestion adapters from stubs to robust allowlisted paths.
3. **4.3 Evaluation Gatekeeping**
   - Add offline datasets + online-style telemetry checks, enforce thresholds in CI.
4. **4.5 Embodied Runtime**
   - Deliver CPU-first perception and speech loop under the same policy engine.
5. **5.1 Persistent Memory**
   - Integrate one vector memory backend with deterministic retrieval tests.
6. **5.2 Offline Learning + Promotion**
   - Nightly learning with canary checks and model registry rollback safety.
7. **5.3 Orchestration Hardening**
   - Introduce `Ray` or `Airflow` only when scheduling scale/ops complexity justifies it.

---

## ⚙️ Engineering Standards

- **Standardized Tracing:** All functions decorated with `@sentinel`.
- **CPU-First Design:** Optimization target is 4-core Intel i5 hardware.
- **Safety Interlock:** No action executed without policy check or user confirmation.

---

## 📂 Current Filesystem Focus

- `training/`: Core model and trainer logic.
- `actions/`: The agency layer (router, policy).
- `tools/`: The system interaction adapters.
- `docs/`: The comprehensive spec and guideline suite.

---

## Last Updated

2026-04-05
