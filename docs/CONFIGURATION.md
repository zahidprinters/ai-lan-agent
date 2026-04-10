# AI Lan Configuration Guide ⚙️

This document centralizes all configuration options, environment variables, and experiment profiles used in the AI Lan project.

---

## 🏗️ Experiment Profiles

Experiment profiles are pre-configured sets of hyperparameters. Set the **`AI_LAN_EXP_PROFILE`** environment variable to one of the following before training:

| Profile | Purpose | Epochs | Batch | Block | Hidden | Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `debug` | Fast logic testing | 2 | 4 | 8 | 16 | `char_mlp` |
| `baseline` | Simple Bigram floor | 50 | 32 | 16 | 64 | `bigram` |
| `transformer_small` | Entry transformer | 50 | 16 | 16 | 32 | `transformer` |
| `transformer_medium` | Deep experiment | 50 | 16 | 16 | 64 | `transformer` |
| `transformer_large` | Large transformer | 50 | 8 | 16 | 128 | `transformer` |

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
- **`AI_LAN_DEVICE`**: Runtime device selection (`cpu` or `cuda` when available).
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

### External Service Keys (Optional)

- **`TAVILY_API_KEY`**: API key for live Tavily search integration in the optional Phase 4 web-search stack.

### Phase 4.5 Local Brain / Embodied Settings

- **`AI_LAN_REASONING_BACKEND`**: Planner backend (`classic` or `llama_cpp`).
- **`AI_LAN_LLAMACPP_MODEL_PATH`**: GGUF model path for local llama-cpp reasoning.
- **`AI_LAN_LLAMACPP_CTX`**: Context window for llama-cpp runtime.
- **`AI_LAN_LLAMACPP_THREADS`**: CPU thread count for llama-cpp.
- **`AI_LAN_LLAMACPP_GPU_LAYERS`**: GPU layer offload count (`0` for CPU-only).
- **`AI_LAN_PERCEPTION_ENABLED`**: Enable background perception loop (`0`/`1`).
- **`AI_LAN_PERCEPTION_INTERVAL_SEC`**: Perception sampling interval in seconds.
- **`AI_LAN_STT_ENABLED`**: Enable speech-to-text runtime wiring (`0`/`1`).
- **`AI_LAN_TTS_ENABLED`**: Enable text-to-speech runtime wiring (`0`/`1`).
- **`AI_LAN_VOSK_MODEL_PATH`**: Local path to Vosk model directory used by offline STT listener.
- **`AI_LAN_MEMORY_BACKEND`**: Memory backend selector (`none` or `chroma`).
- **`AI_LAN_CHROMA_PATH`**: Local storage path for Chroma backend.

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

2026-04-10

---

## Machine-Specific Baseline (Small-Machine Safe)

The current project machine is an i5-8350U laptop with 16 GB RAM and integrated Intel UHD 620 graphics (no discrete GPU).

Recommended baseline for reliable local runs:

- `AI_LAN_DEVICE=cpu`
- `AI_LAN_USE_AMP=0`
- `AI_LAN_EXP_PROFILE=transformer_small`
- `AI_LAN_BATCH_SIZE=8`
- `AI_LAN_BLOCK_SIZE=16`

For full hardware details, see `docs/HARDWARE_PROFILE.md`.
