# AI Lan Configuration Guide ⚙️

This document centralizes all configuration options, environment variables, and experiment profiles used in the AI Lan project.

---

## 🏗️ Experiment Profiles

Experiment profiles are pre-configured sets of hyperparameters. Set the **`AI_LAN_EXP_PROFILE`** environment variable to one of the following before training:

| Profile | Purpose | Epochs | Batch | Block | Hidden | Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `debug` | Fast logic testing | 2 | 4 | 8 | 16 | `char_mlp` |
| `baseline` | Simple Bigram floor | 50 | 32 | 16 | 64 | `bigram` |
| `transformer_small` | Entry transformer (i5 default) | 50 | 8 | 16 | 32 | `transformer` |
| `transformer_medium` | Deep experiment (i5-safe) | 50 | 8 | 16 | 64 | `transformer` |
| `transformer_large` | Large transformer | 50 | 8 | 16 | 128 | `transformer` |

When `AI_LAN_EXP_PROFILE` is not set, runtime config now defaults to `transformer_small` to stay aligned with the active i5/16 GB machine profile.

---

## 🌍 Environment Variables

You can override any individual setting by setting its corresponding environment variable:

### Training & Architecture

- **`AI_LAN_MODEL_TYPE`**: `bigram`, `char_mlp`, `transformer`, `lstm`, or `gru`.
- **`AI_LAN_EPOCHS`**: Number of full passes over the dataset.
- **`AI_LAN_BATCH_SIZE`**: Number of samples per training step.
- **`AI_LAN_BLOCK_SIZE`**: Context window length (sequence length).
- **`AI_LAN_HIDDEN_SIZE`**: Dimensionality of embeddings and hidden layers.
- **`AI_LAN_LEARNING_RATE`**: Base step size for the optimizer.
- **`AI_LAN_PATIENCE`**: Number of epochs to wait for improvement before **Early Stopping**.
- **`AI_LAN_TRAIN_RATIO`**: Train/validation split ratio (must be > 0 and < 1).
- **`AI_LAN_N_LAYER`**: Number of model layers (transformer/recurrent models).
- **`AI_LAN_N_HEAD`**: Number of attention heads (transformer).
- **`AI_LAN_DROPOUT`**: Dropout rate.
- **`AI_LAN_STOCHASTIC_DEPTH`**: Stochastic depth rate.
- **`AI_LAN_LR_WARMUP_STEPS`**: Warmup steps for LR schedule.
- **`AI_LAN_LR_WARMUP_EPOCHS`**: Warmup epochs for LR schedule.
- **`AI_LAN_DEVICE`**: Runtime device selection. Project default is `cpu` for machine-safe behavior.
- **`AI_LAN_USE_AMP`**: Enable mixed precision (`0`/`1`).

### Tokenization

- **`AI_LAN_TOKENIZER_TYPE`**: `char` or `bpe`.
- **`AI_LAN_TOKENIZER_PATH`**: Explicit path to save/load tokenizer metadata.

### Generation & Inference

- **`AI_LAN_GENERATE_TEMPERATURE`**: Creativity control (0.0 to 2.0).
- **`AI_LAN_GENERATE_TOP_K`**: Limit sampling to top K tokens.
- **`AI_LAN_GENERATE_TOP_P`**: Nucleus sampling threshold (0.0 to 1.0).
- **`AI_LAN_GENERATE_TOKENS`**: Number of tokens to generate.
- **`AI_LAN_GENERATE_BATCH_SIZE`**: Number of independent samples per request.
- **`AI_LAN_GENERATE_START_TEXT`**: Prompt prefix for generation.
- **`AI_LAN_GENERATE_SEED`**: Optional deterministic seed.

### Logging & Debugging

- **`AI_LAN_DEBUG`**: Enable sentinel function entry/exit logging (`0`/`1`).
- **`AI_LAN_TRACE`**: Enable line-level variable tracing (`0`/`1`).
- **`AI_LAN_PROFILE`**: Enable timing and memory profiling (`0`/`1`).
- **`AI_LAN_DEBUG_LOGFILE`**: Optional path for sentinel logs.
- **`AI_LAN_TRACE_STDOUT`**: Mirror trace output to console (`0`/`1`) when trace is enabled.

`training/config.py` now centralizes these toggles in `ProjectConfig.debug` (`DebugSettings`) while preserving the existing compatibility fields (`debug_trace`, `debug_profile`).

### Policy Runtime Config

- **`AI_LAN_POLICY_CONFIG_PATH`**: Optional path override for router action policy config (defaults to `config/policies.yaml`).
  The policy file supports `allow_actions`, `deny_actions`, and `require_confirmation` lists.
- **`AI_LAN_SETTINGS_PATH`**: Optional path override for runtime settings (defaults to `config/settings.yaml`).
  CLI control-center settings commands (`/settings show`, `/settings set`) read and write this file.
- **`AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS`**: Enable Android ADB side effects (`0`/`1`). Keep disabled by default.
- **`AI_LAN_ANDROID_ALLOWED_PACKAGES`**: Comma-separated allowlist for Android package launches. `android.launch_app` stays blocked until the target package is listed here.
- **`AI_LAN_ANDROID_ALLOWED_DEVICE_IDS`**: Optional comma-separated allowlist for Android device IDs. When set, side-effect Android actions must include an explicit `device_id` from this list.
- **`AI_LAN_ANDROID_ADB_TIMEOUT_SECONDS`**: ADB command timeout in seconds (default `15`, clamped to `1..120`) for deterministic failure instead of hanging subprocess calls.
- **`AI_LAN_PC_PROCESS_LIST_TIMEOUT_SECONDS`**: `tasklist` timeout in seconds (default `8`, clamped to `1..60`) for deterministic `pc.list_running_apps` failure instead of hanging process probes.

Storage retention and housekeeping defaults (`config/settings.yaml`):

- **`storage_temp_retention_days`**: Retention window for generic temp artifacts.
- **`storage_benchmark_retention_days`**: Retention window for benchmark artifacts under `temp/benchmarks`.
- **`storage_download_retention_days`**: Retention window for cache/download artifacts under `temp/downloads`.
- **`storage_temp_soft_limit_mb`**: Soft-limit threshold used by dashboard storage health warnings.

Android screenshot captures are also constrained to paths under `temp/` to keep device artifacts inside the project scratch area.

### External Service Keys (Optional)

- **`TAVILY_API_KEY`**: API key for live Tavily search integration in the optional Phase 4 web-search stack.

### Phase 4.5 Local Brain / Embodied Settings

- **`AI_LAN_REASONING_BACKEND`**: Planner backend (`classic` or `llama_cpp`).
- **`AI_LAN_LLAMACPP_MODEL_PATH`**: GGUF model path for local llama-cpp reasoning.
- **`AI_LAN_LLAMACPP_MODEL_PROFILE`**: Default GGUF profile selector (`phi4_q4km` or `llama8b_q4km`) when no explicit model path is set.
- **`AI_LAN_LLAMACPP_CTX`**: Context window for llama-cpp runtime.
- **`AI_LAN_LLAMACPP_THREADS`**: CPU thread count for llama-cpp.
- **`AI_LAN_LLAMACPP_GPU_LAYERS`**: GPU layer offload count (`0` for CPU-only).
- **`AI_LAN_LLAMACPP_RESIDENT`**: Keep the selected GGUF model resident between turns (`0`/`1`).
- **`AI_LAN_LLAMACPP_UNLOAD_RAM_PCT`**: Unload the resident model and fall back to classic planning when host RAM pressure crosses this percent.
- **`AI_LAN_MODEL_ROUTER_ENABLED`**: Enable simple-vs-complex GGUF model routing (`0`/`1`).
- **`AI_LAN_MODEL_ROUTER_SIMPLE_MODEL_PATH`**: Optional GGUF path used when dynamic planning marks a request as simple.
- **`AI_LAN_MODEL_ROUTER_COMPLEX_MODEL_PATH`**: Optional GGUF path used for complex requests when routing is enabled.
- **`AI_LAN_REASONING_DYNAMIC_PLANNING`**: Let the controller classify requests as `simple` or `complex` for model routing (`0`/`1`).
- **`AI_LAN_REASONING_PLAN_STEPS_MIN`**: Minimum acceptable plan length enforced by planner validation and repair (clamped to `3`-`5`).
- **`AI_LAN_REASONING_PLAN_STEPS_MAX`**: Maximum acceptable plan length enforced by planner validation and repair (clamped to `3`-`5`).
- **`AI_LAN_REASONING_TELEMETRY_ENABLED`**: Write structured inference success/fallback events to the agent log (`0`/`1`).
- **`AI_LAN_AGENT_LOG_PATH`**: JSONL output path for inference-manager telemetry.
- **`AI_LAN_TOOL_LOG_PATH`**: JSONL output path for structured tool dispatch attempts/results.
- **`AI_LAN_ERROR_LOG_PATH`**: JSONL output path for structured runtime/tool exceptions.
- **`AI_LAN_REFLECTION_RETRIES`**: Max reflection retries per ReAct step (default `1`).
- **`AI_LAN_REFLECTION_RETRIES_PER_TURN`**: Max total reflection retries before the runtime stops retrying in a turn-like sequence (default `3`).
- **`AI_LAN_REFLECTION_REQUIRED_ON_FAILURE`**: Require an explicit reflection decision record before retrying failed or empty-result tool calls (`0`/`1`).
- **`AI_LAN_STREAM_TOOL_TRIGGER_ENABLED`**: Enable token-stream interception while llama-cpp is generating (`0`/`1`).
- **`AI_LAN_STREAM_TOOL_TRIGGER_PATTERN`**: Optional fallback text trigger used for stream interception when JSON action payloads have not completed yet.
- **`AI_LAN_KV_CACHE_MAX_TURNS`**: Maximum un-compacted recent turn/thought/observation count before prompt compaction runs.
- **`AI_LAN_CONTEXT_SUMMARY_ENABLED`**: Enable compacted summaries for older turns/thoughts/observations before prompt assembly (`0`/`1`).
- **`AI_LAN_CONTEXT_SUMMARY_TARGET_TOKENS`**: Approximate token budget used by the compaction summaries.
- **`quality_guardrail_min_score`** (`config/settings.yaml`): Minimum quality score required before `scripts/model_registry.py activate` can promote a candidate version.
- **`quality_guardrail_baseline_model`** (`config/settings.yaml`): Optional registry version that a candidate must meet or exceed in the quality benchmark artifacts under `runs/quality/`.
- **`dynamic_safety_enabled`** (`config/settings.yaml`): Enables dynamic safety escalation from runtime context/perception signals.
- **`sensitive_context_keywords`** (`config/settings.yaml`): Comma-separated keywords used to classify sensitive context (for example `password,otp,bank`).
- **`AI_LAN_PERCEPTION_ENABLED`**: Enable background perception loop (`0`/`1`).
- **`AI_LAN_PERCEPTION_INTERVAL_SEC`**: Perception sampling interval in seconds.
- **`AI_LAN_PERCEPTION_MAX_INTERVAL_SEC`**: Maximum interval cap for adaptive perception backoff.
- **`AI_LAN_PERCEPTION_ADAPTIVE`**: Enable adaptive backoff when screen summary is unchanged (`0`/`1`).
- **`AI_LAN_RUNTIME_CONTEXT_MAX_CHARS`**: Character budget used to cap each runtime-context section.

When enabled, the latest compact OCR/screen summary is stored in session state and injected into runtime context for the planner.
Adaptive perception reduces idle CPU load by increasing sample interval when the screen summary stays unchanged.

Active in the current 4.5A foundation slice:

- `core/inference/engine.py` now owns GGUF runtime loading, resident-cache reuse, and deterministic fallback reasons.
- `core/inference/residency.py` monitors host RAM pressure and triggers resident unload when the configured threshold is exceeded.
- `core/inference/model_router.py` builds a pressure-aware GGUF candidate chain and can fall back from preferred complex/simple models to cheaper secondary candidates before classic fallback.
- `core/inference/context_manager.py` and `core/inference/kv_cache_manager.py` compact older prompt state with role-aware summaries and head/tail runtime-context preservation before context growth degrades stability.
- `agents/react/planner.py` now provides plan-quality requirements plus model-plan validation/repair instead of injecting a fixed heuristic plan body.
- `agents/react/reflection.py` records explicit retry/skip decisions before retries are attempted.
- `agents/react/tool_risk.py` and `agents/react/tool_schema.py` expose richer tool risk metadata (`risk_tier`, `policy_mode`, `risk_reasons`) to the planner and runtime logs.
- `agents/react/runtime_guard.py` now enforces pre-dispatch runtime checks so streamed tool triggers must align with validated plan metadata before action dispatch.
- `agents/react/runtime_guard.py` also binds streamed actions to a canonical execution contract so runtime dispatch can reject payload drift before `_run_payload` executes.
- `agents/react/structured_logging.py` writes structured agent, tool, and error JSONL logs under `temp/logs/` by default.

- **`AI_LAN_STT_ENABLED`**: Enable speech-to-text runtime wiring (`0`/`1`).
- **`AI_LAN_TTS_ENABLED`**: Enable text-to-speech runtime wiring (`0`/`1`).
- **`AI_LAN_VOSK_MODEL_PATH`**: Local path to Vosk model directory used by offline STT listener.
- **`AI_LAN_MEMORY_BACKEND`**: Memory backend selector (`none` or `chroma`).
- **`AI_LAN_CHROMA_PATH`**: Local storage path for Chroma backend.

Planned for later 4.5A slices (documented target, not active yet):

- **`AI_LAN_REFLECTION_MAX_RETRIES`**: Reflection/retry ceiling per turn.
- **`AI_LAN_PROMPT_XML_MODE`**: Enforce XML-structured prompt contract for planner output (`0`/`1`).
- **`AI_LAN_TOOL_SCHEMA_TRANSLATOR_ENABLED`**: Enable automatic translation of tool signatures/metadata into model prompt schema (`0`/`1`).
- **`AI_LAN_TOOL_RISK_POLICY_PATH`**: Optional risk-tier mapping file (`safe`/`medium`/`dangerous`) for tool execution controls.

When `AI_LAN_MEMORY_BACKEND=chroma`, runtime context retrieval and memory search use ChromaDB first for vector scoring and automatically fall back to the local JSON vector index if Chroma is unavailable.

### Model Promotion Guardrails

- `scripts/benchmark_quality.py` writes machine-readable benchmark artifacts to `runs/quality/`.
- `scripts/model_registry.py activate --version <version>` now requires a matching artifact for the target version before it can become active.
- Promotion is blocked when the candidate artifact is missing, when the score is below `quality_guardrail_min_score`, or when it regresses below `quality_guardrail_baseline_model`.

### Dynamic Safety Escalation

- Runtime context now emits `sensitive_context` when perception/query text matches configured sensitive keywords.
- Policy evaluation consumes that context and upgrades selected risky actions (for example typing and screen OCR/screenshot reads) to strong confirmation mode.
- In non-sensitive context, existing confirmation behavior is preserved.

---

## 📂 Project Paths

Managed automatically but overrideable:

- **`AI_LAN_DATA_PATH`**: Path to `input.txt` (Default: `data/input.txt`).
- **`AI_LAN_RUNS_DIR`**: Directory for experiment artifacts (Default: `runs/`).
- **`AI_LAN_MODEL_PATH`**: Final model output (Default: `models/char_model.pt`).
- **`AI_LAN_BEST_MODEL_PATH`**: Best-model checkpoint path.
- **`AI_LAN_TOKENIZER_PATH`**: Tokenizer save/load path.
- **`AI_LAN_GENERATE_MODEL_PATH`**: Checkpoint used by generation script.
- **`AI_LAN_GENERATE_TOKENIZER_PATH`**: Tokenizer used by generation script.

---

## Last Updated

2026-04-11

---

## Machine-Specific Baseline (Small-Machine Safe)

The current project machine is an i5-8350U laptop with 16 GB RAM and integrated Intel UHD 620 graphics (no discrete GPU).

Recommended baseline for reliable local runs:

- `AI_LAN_DEVICE=cpu`
- `AI_LAN_USE_AMP=0`
- `AI_LAN_EXP_PROFILE=transformer_small`
- `AI_LAN_BATCH_SIZE=8`
- `AI_LAN_BLOCK_SIZE=16`

Work that exceeds this machine profile should be queued to the heavy-machine lanes (`Phase X5/X6`) documented in `docs/PHASE_X_MACHINE_PLAN.md`.

For full hardware details, see `docs/HARDWARE_PROFILE.md`.
