# AI Lan API Reference 📖

This document provides a detailed breakdown of the functions, classes, and modules within the AI Lan project. It specifies expected input data types and the resulting outputs for every major component.

---

## 🛡️ Module: `debug_utils.py`

### `@sentinel` (Decorator)

- **Description:** Unified observability decorator for debugging and profiling.
- **Environment Toggles:**
  - `AI_LAN_DEBUG`: Basic entry/exit logging.
  - `AI_LAN_TRACE`: Line-by-line local variable tracking.
  - `AI_LAN_PROFILE`: CPU/Memory performance profiling.

---

## ⚙️ Module: `training/config.py`

### `ProjectConfig` (Dataclass)

- **Description:** Central typed configuration for paths, training hyperparameters, generation controls, and runtime flags.

### `load_config() -> ProjectConfig`

- **Description:** Loads project configuration from defaults + environment variable overrides + optional profile presets.
- **Inputs:** None.
- **Returns:** Populated `ProjectConfig` instance.
- **Validation:** Rejects invalid values such as `AI_LAN_TRAIN_RATIO` outside `(0, 1)`.

---

## 💾 Module: `training/checkpoints.py`

### `save_checkpoint(...) -> None`

- **Description:** Serializes model weights, optimizer state, and tokenizer metadata to a `.pt` file.
- **Key Inputs:**
  - `path` (Path): Destination for the checkpoint file.
  - `model` (nn.Module): The PyTorch model to save.
  - `tokenizer` (Any): The tokenizer used during training.
- **Returns:** None.

### `load_checkpoint(path: Path) -> dict`

- **Description:** Loads a previously saved model state and metadata.
- **Inputs:** `path` (Path): Path to the `.pt` file.
- **Returns:** A dictionary containing model weights and configuration metadata.

### `infer_vocab_size_from_checkpoint(checkpoint: dict, default: int | None = None) -> int`

- **Description:** Infers the vocabulary size from checkpoint metadata, model state, or an explicit fallback.
- **Behavior:** Raises a clear error if no positive vocabulary size can be resolved.

### `load_config_from_checkpoint(checkpoint: dict, fallback: ProjectConfig | None = None) -> ProjectConfig`

- **Description:** Reconstructs a `ProjectConfig` from saved checkpoint metadata.
- **Compatibility Behavior:** Unknown legacy keys are ignored, path-like strings are converted back to `Path` objects, and the optional fallback config is used when the checkpoint does not carry a `config` payload.

### `load_model_from_checkpoint(checkpoint: dict, tokenizer_vocab_size: int | None = None, fallback_config: ProjectConfig | None = None, allow_quantized: bool = True) -> tuple[nn.Module, ProjectConfig, int]`

- **Description:** Builds the correct architecture from checkpoint metadata and loads the saved weights.
- **Returns:** `(model, resolved_config, resolved_vocab_size)`.
- **Behavior:** Quantized checkpoints are supported for inference-only paths; callers can set `allow_quantized=False` to block them with a clear error message.

### `normalize_run_summary(summary: dict, summary_path: Path, project_data_path: Path) -> dict`

- **Description:** Normalizes legacy flat summaries and newer nested `metrics` / `hyperparameters` run summaries into one display-ready structure.

### `build_sorted_summaries(runs_dir: Path, project_data_path: Path) -> list[dict]`

- **Description:** Reads all run summaries from disk, normalizes them, annotates compatibility fields, and returns them in leaderboard order.

### `save_run_artifacts(...) -> None`

- **Description:** Saves per-run JSON summary and sample text files, then refreshes the canonical run index and the legacy compatibility alias.

---

## 🧠 Module: `training/trainer.py`

### `Trainer` (Class)

- **Description:** The primary engine for training models in the AI Lan ecosystem.
- **Inputs (Constructor):** `config`, `model`, `tokenizer`, `optimizer`, `loss_fn`.

#### `Trainer.run(train_loader, val_loader, start_epoch) -> tuple`

- **Description:** Executes the full training loop through all configured epochs.
- **Inputs:**
  - `train_loader` (DataLoader): Training data stream.
  - `val_loader` (DataLoader): Validation data stream.
- **Returns:** `(best_val_loss, final_train_loss, final_val_loss)`.

---

## 🧮 Module: `training/factory.py`

### `build_model(model_type, config, vocab_size) -> nn.Module`

- **Description:** Dynamically constructs requested architecture.
- **Supported values:** `char_mlp`, `bigram`, `transformer`, `lstm`, `gru`.

---

## 📝 Module: `tokenizer/`

### `CharTokenizer` (Class)

- **Description:** Maps individual characters to unique integers.
- **Methods:**
  - `encode(text: str) -> list[int]`: Converts text into a sequence of token IDs.
  - `decode(ids: list[int]) -> str`: Reconstructs text from token IDs.

### `BPETokenizer` (Class)

- **Description:** Maps subword units (merges) to integers for higher efficiency.
- **Methods:**
  - `train(files: list[str]) -> None`: Optimizes vocabulary based on input corpus.
  - `encode(text: str) -> list[int]`: Converts text into subword token sequences.

### `tokenizer.factory.load_tokenizer(path) -> TokenizerType`

- **Description:** Auto-detects tokenizer type from serialized file and loads char/BPE implementation.

### `tokenizer.factory.get_tokenizer_by_type(...) -> TokenizerType`

- **Description:** Creates or loads tokenizer based on requested type and available corpus.

---

## ✨ Module: `training/inference.py`

### `sample_text(...) -> str`

- **Description:** Generates text using a trained model.
- **Key Inputs:**
  - `model`: Trained neural network.
  - `start_text` (str): The seed string to begin generation.
  - `temperature` (float): Creativity control (Higher = more random).
  - `top_k` (int): Limits sampling to the top K most likely next tokens.
- **Returns:** The generated string.

### `sample_texts(...) -> list[str]`

- **Description:** Generates multiple independent sequences in one call.

### `streaming_text_generator(...) -> generator`

- **Description:** Yields generated output token-by-token or text-by-text.

---

## 🌐 Module: `tools/web_ingest.py`

### `IngestionSource` (Dataclass)

- **Description:** Declares a trusted text source for ingestion.
- **Fields:** `name`, `source_type`, `location`, `trust_score`.

### `run_ingestion_pipeline(sources, merged_output_path, report_output_path) -> IngestionReport`

- **Description:** Fetches configured text sources, normalizes content, deduplicates documents and lines, scores quality/trust, and writes merged corpus plus JSON report artifacts.

### `score_source_quality(text, trust_score) -> tuple[float, float]`

- **Description:** Applies heuristic scoring for source cleanliness and trustworthiness before merge.

---

## 🧩 Module: `tools/memory_store.py`

### `add_memory_entry(kind, content, metadata=None, db_path=None) -> MemoryEntry`

- **Description:** Stores a memory record with automatic tokenization and summary generation.

### `store_conversation_summary(user_text, assistant_text, metadata=None, db_path=None) -> MemoryEntry`

- **Description:** Persists a conversation turn summary for long-term retrieval.

### `retrieve_relevant_memories(query, limit=5, min_score=0.05, kind=None, db_path=None) -> list[MemoryHit]`

- **Description:** Returns ranked memory hits using deterministic token-overlap retrieval.

### `get_recent_memories(limit=10, kind=None, db_path=None) -> list[MemoryEntry]`

- **Description:** Lists recent persisted memory entries from the local SQLite memory store.

---

## 🧠 Module: `tools/context_builder.py`

### `retrieve_corpus_snippets(query, merged_corpus_path=None, limit=5, min_score=0.05) -> list[dict]`

- **Description:** Retrieves ranked snippet candidates from the merged ingestion corpus based on token-overlap scoring.

### `build_prompt_context(query, ...) -> dict`

- **Description:** Combines ranked memory hits and ranked corpus snippets into a context payload suitable for prompt assembly.

---

## 🖥️ Module: `tools/pc_control.py`

### `get_system_status() -> dict`

- **Description:** Returns read-only machine metadata for safe local context.

### `list_running_apps(limit=25) -> list[str]`

- **Description:** Returns a read-only list of running app/process image names.

---

## 📱 Module: `tools/android_control.py`

### `list_devices() -> list[dict]`

- **Description:** Read-only ADB device discovery.

### `launch_app(...)`, `tap_screen(...)`, `swipe_screen(...)`, `capture_screenshot(...)`

- **Description:** Android control adapters behind policy confirmation and safe-mode gating.
- **Phase 4.2 Guards:** `launch_app(...)` requires `AI_LAN_ANDROID_ALLOWED_PACKAGES`; side-effect Android actions can be pinned with `AI_LAN_ANDROID_ALLOWED_DEVICE_IDS`; `capture_screenshot(...)` only writes under `temp/`.

---

## 🔄 The ReAct Pattern (Thought -> Action -> Observation)

AI Lan uses a structured loop for autonomous tool use.

### 1. The Request (Input)
The model generates a "Thought" and an "Action" in JSON format:
```json
{
  "thought": "I need to know the current CPU usage.",
  "action": "pc.get_system_status",
  "args": {}
}
```

### 2. The Dispatch (Router)
The `Action Router` receives the payload and:
- **Validates:** Checks if `pc.get_system_status` exists and args match.
- **Authorizes:** Checks `safety/policy_engine.py`. Read-only actions are allowed immediately; write actions (like `pc.open_app`) return `status: "confirmation_required"`.
- **Executes:** Calls the underlying Python tool.

### 3. The Observation (Output)
The router returns an `ActionExecutionResult` which the model reads as its next context:
```json
{
  "status": "executed",
  "action": "pc.get_system_status",
  "observation": {
    "platform": "win32",
    "cpu_usage": "15.4%",
    "memory_free_mb": 4096
  }
}
```

---

### `scripts/export_onnx.py`

- Exports trained checkpoints into ONNX format.
- Requires both `onnx` and `onnxruntime` for a successful deployment workflow.
- Writes a small `.meta.json` sidecar that stores the block size and tokenizer metadata used by the standalone inference path.

### `scripts/quantize_model.py`

- Produces dynamic int8 quantized checkpoints.
- The resulting artifacts are intended for PyTorch inference paths; the generic export helper rejects them until a dedicated export route exists.

### `scripts/infer_simple.py`

- Runs standalone PyTorch or ONNX inference.
- The PyTorch path now resolves config/tokenizer metadata from the checkpoint first.
- The ONNX path uses the export sidecar metadata when available and intentionally uses greedy decoding for stable portability.

### `scripts/ingest_sources.py`

- Loads a JSON source list and writes merged/report artifacts under `temp/ingestion/` by default.

### `scripts/memory_store.py`

- Provides CLI operations to add memories, store conversation summaries, search retrieved memories, and list recent entries.

### `scripts/benchmark_tools.py`

- Runs tool benchmark cases and reports tool success rate, safety refusal quality, and latency metrics.

### `scripts/offline_learning_pipeline.py`

- Builds a learning dataset from memory/corpus artifacts, runs a canary gate, and can optionally promote a real candidate model.
- Placeholder artifacts are blocked from promotion; `--candidate-model` should point to an actual model file.

### `scripts/model_registry.py`

- Provides model registry/versioning and rollback CLI workflows.

### `scripts/list_runs.py`

- Displays normalized leaderboard output for either the project-only index or the full run set.

### `scripts/rebuild_run_index.py`

- Rebuilds the canonical run index and the legacy compatibility alias from normalized summaries.

### `scripts/validate_installation.py`

- Validates the local environment, including ONNX tooling, and exits nonzero when required dependencies are missing.

---

## Updated Router Actions

- `memory.search`: policy-gated memory retrieval action.
- `context.build`: policy-gated context assembly action combining memory + corpus snippets.
- `pc.get_system_status`: read-only machine metadata action.
- `pc.list_running_apps`: read-only process listing action.
- `android.list_devices`: read-only Android device discovery action.
- `android.launch_app` / `android.tap` / `android.swipe` / `android.capture_screenshot`: confirmation-gated Android adapter actions.

Future tool additions should be selected from [OPEN_SOURCE_REFERENCE.md](OPEN_SOURCE_REFERENCE.md), wrapped behind the local router and safety layers, and covered by tests before they reach the live path.

---

## Planned Embodied Modules

These modules are the next target for the CPU-first embodied runtime:

- `perception/vision/screen_capture.py`: low-latency desktop screenshot capture.
- `perception/vision/camera.py`: camera frame capture and preprocessing.
- `perception/vision/ocr.py`: OCR extraction from screenshots and photos.
- `perception/vision/object_detection.py`: optional object detection and grounding.
- `perception/audio/speech_to_text.py`: offline speech transcription.
- `perception/audio/text_to_speech.py`: offline speech synthesis.
- `perception/audio/mic.py`: microphone capture and buffering.
