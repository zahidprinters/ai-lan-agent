# AI Lan User Guide 📘

Welcome to **AI Lan**! This guide provides end-users with the information needed to train, test, and use local language models effectively.

---

## 🛠️ Getting Started

Before performing any action, ensure you are in the project's root directory and have your Python environment set up correctly.

### 1. Launching the Dashboard

The dashboard is the central hub for all AI Lan actions. To launch it, run the following command in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File main.ps1
```

Once the dashboard is open, you can simply type the **number** corresponding to the action you wish to perform (e.g., `3` to train).

---

## 🚀 Key Actions & Workflows

### 📍 Action 3: Train Model

- **What it does:** Reads your training data (`data/input.txt`) and trains the selected model.
- **Result:** Saves a `models/char_model_best.pt` file.

### 📍 Action 4: Generate Text

- **What it does:** Uses your trained model to generate new text based on a prompt.
- **Result:** Displays the generated text in your console.

### 📍 Action 11: Dataset Report

- **What it does:** Analyzes the quality of your training data.

---

## 🚀 Advanced Workflows

### 📍 Deploying to High-Performance Environments

For production or edge deployment, use the **ONNX** or **Quantization** pipelines:

1. **Export to ONNX**: `python scripts/export_onnx.py --model models/char_model_best.pt`
2. **Quantize for CPU**: `python scripts/quantize_model.py --model models/char_model_best.pt`
3. **Fast Evaluation**: Use `scripts/evaluate.py` to benchmark performance metrics.

The export path now checks for `onnx` and `onnxruntime` up front, and the ONNX inference path reads the metadata sidecar written during export. Quantized checkpoints are currently intended for the PyTorch inference path, so keep them out of generic export workflows.

### 📍 Current Machine Baseline (i5 / 16 GB)

For this machine, keep training and runtime in CPU-safe mode:

```powershell
$env:AI_LAN_DEVICE = "cpu"
$env:AI_LAN_USE_AMP = "0"
$env:AI_LAN_EXP_PROFILE = "transformer_small"
$env:AI_LAN_BATCH_SIZE = "8"
$env:AI_LAN_BLOCK_SIZE = "16"
python training/train_char_model.py
```

If a workflow requires higher memory, longer sweeps, or GPU-dependent acceleration, move it to `Phase X5/X6` in `docs/PHASE_X_MACHINE_PLAN.md`.

### 📍 Real-World Workflow: Agentic ReAct

To experiment with "reasoning" workflows, prepare a dataset that includes "Thought/Action/Observation" patterns:

1. **Prepare Data**: Craft `input.txt` with examples like:
   `User: What is AI? Thought: I should search for AI definition. Action: WebSearch("AI definition") Observation: AI is...`
2. **Train Model**: Use a larger `transformer` profile.
3. **Run Inference**: Use `training/inference.py` with `stop_sequences=["Observation:"]`.

### 📍 Real-World Workflow: Narrative Logic

For high-quality storytelling logic, use the pre-curated TinyStories dataset:

1. **Fetch Data**: Run `python scripts/fetch_tinystories.py`.
2. **Train Model**: Set `AI_LAN_DATA_PATH="data/tinystories.txt"` and train for at least 10 epochs.
3. **Quantize**: To shrink your story-brain for mobile deployment, run `python scripts/quantize_model.py`.

### 📍 Real-World Workflow: Continuous Internet Data Feed

To improve model quality using external free resources:

1. Curate trusted text sources (public datasets, docs, articles, transcripts).
2. Normalize and deduplicate corpus (`python scripts/clean_dataset.py`).
3. Merge curated sources into one corpus (`scripts/merge_corpus.ps1`).
4. Run quality report (`python scripts/data_report.py`).
5. Retrain with fixed profile and compare run summaries in `runs/`.

When you review run summaries, the leaderboard tooling now normalizes both legacy flat summaries and newer nested summaries automatically, so you can compare old and new runs side by side.

### 📍 Real-World Workflow: Embodied CPU Mode

If you want the lightest embodied setup for a CPU-only machine, start with:

1. **Eyes:** `mss` for screenshots, `OpenCV` for frame handling, and `Tesseract` for OCR.
2. **Ears:** `Vosk` for offline speech-to-text.
3. **Voice:** `pyttsx3` for offline speech output.
4. **Brain:** `llama.cpp` for local reasoning.

Once that works, upgrade selectively with `whisper.cpp`, `Coqui TTS`, `EasyOCR`, or `Ultralytics` only if the extra cost is justified.

Voice mode quick start:

```powershell
python scripts/launch.py --mode voice
```

CLI control center quick start:

```powershell
python scripts/chat_cli.py
```

Inside chat mode, use these commands to inspect or update behavior without leaving the session:

- `/control` shows all control-center commands.
- `/policy show` prints active allow/deny/confirmation action lists.
- `/policy add <allow|deny|confirm> <action_name>` updates policy lists in the active policy file and reloads policy runtime.
- `/policy remove <allow|deny|confirm> <action_name>` removes an action from a policy list and reloads policy runtime.
- `/settings show [prefix]` prints values from the active `config/settings.yaml` file (or path override).
- `/settings set <key> <value>` writes a scalar value to settings (`true`/`false`, numbers, and quoted/unquoted strings are supported).
- `/env show [prefix]` prints current process environment values, optionally filtered by prefix.
- `/env set <KEY> <VALUE>` sets a process environment variable for the active chat process.
- `/env unset <KEY>` clears a process environment variable from the active chat process.

Policy and settings commands persist changes to disk. Environment commands affect only the running process session and do not edit `.env` files.

Web control center quick start:

```powershell
python scripts/chat_web.py
```

Open the dashboard chat page and use the new **Control center** section to manage the same controls without typing every command manually.

- Policy editor: add/remove actions from allow, deny, and confirmation lists.
- Settings editor: set and review values in `config/settings.yaml` (or `AI_LAN_SETTINGS_PATH`).
- Environment editor: show/set/unset `AI_LAN_*` environment values for the active runtime process.
- Capability panel: one-click toggles for mic (STT), speaker (TTS), camera/perception loop, and OCR availability visibility.

The web chat command buttons and form submissions send the same slash commands used by CLI chat, so behavior remains consistent between CLI and web runtime surfaces.

In CLI and voice chat modes, the local planner can now take a small bounded action-observation loop before replying, but any write-like action still stops for confirmation.
Planner tool selection is grounded in a structured tool schema generated from the router registry, so the model sees available actions, arguments, and confirmation hints instead of only raw tool names.
Before dispatch, streamed tool triggers are validated against the planner's repaired/validated plan metadata; misaligned or policy-blocked trigger payloads are rejected before tools execute.
The runtime also verifies an execution contract for streamed actions, so if the final dispatch payload drifts from the trigger/guard-approved payload, the action is blocked instead of executed.
If perception is enabled, the latest OCR/screen summary is kept in session state and included in the planner's live runtime context.
That same summary is visible through the dashboard/API state views, and chat sessions now stop background perception resources cleanly when the CLI exits.
For CPU-friendly runtime handling, perception sampling now backs off automatically when the visible screen summary is unchanged, and runtime context sections are capped by a configurable character budget.
Perception sampling also uses a bounded sample count per tick and confidence-filtered OCR extraction so low-confidence tokens do not dominate runtime context.
Perception OCR can now be pinned to a backend (`auto`, `tesseract`, or `easyocr`) with optional EasyOCR fallback and optional OpenCV preprocessing before extraction.
Runtime context now records perception source, confidence, and OCR backend metadata so troubleshooting can distinguish extractor behavior without bypassing policy-routed actions.

Recommended toggles:

```powershell
$env:AI_LAN_STT_ENABLED = "1"
$env:AI_LAN_TTS_ENABLED = "1"
$env:AI_LAN_MEMORY_BACKEND = "chroma"
# Optional Vosk model location
$env:AI_LAN_VOSK_MODEL_PATH = "temp/vosk-model"
# Optional Chroma path
$env:AI_LAN_CHROMA_PATH = "temp/chroma"
```

If Chroma is not available at runtime, AI Lan falls back to the local vector index automatically.

### 📍 Storage Cleanup And Retention

Use the storage cleanup tool to audit or remove old temporary artifacts safely:

```powershell
python scripts/storage_cleanup.py
```

The default is dry-run mode and writes a JSON report to `temp/benchmarks/storage_cleanup_report.json`.
To apply deletions for files older than configured retention windows:

```powershell
python scripts/storage_cleanup.py --apply
```

Retention windows are controlled in `config/settings.yaml` via:

- `storage_temp_retention_days`
- `storage_benchmark_retention_days`
- `storage_download_retention_days`
- `storage_temp_soft_limit_mb`

### 📍 Low-Speed Internet Prefetch (Temp Cache)

To keep working when internet is slow or unstable, prefetch dependencies and model/data assets into `temp/downloads`:

```powershell
python scripts/prefetch_low_bandwidth_assets.py --all-phases --with-model-assets --sync-runtime-paths
```

For model/data-only caching (skip wheel downloads):

```powershell
python scripts/prefetch_low_bandwidth_assets.py --skip-packages --with-model-assets
```

For very slow links, prefetch one HTTP asset at a time:

```powershell
python scripts/prefetch_low_bandwidth_assets.py --skip-packages --with-model-assets --asset tinystories_text
```

This command populates:

- `temp/downloads/phase4`
- `temp/downloads/phase45`
- `temp/downloads/phase5`
- `temp/downloads/models`

After prefetching, `scripts/fetch_tinystories.py` reuses the local cache before attempting network download.

### 📍 Phase 4/5 Expansion Note

If you are extending AI Lan beyond the current user workflows, start from [OPEN_SOURCE_REFERENCE.md](OPEN_SOURCE_REFERENCE.md) and keep to one project per capability.
The shortest safe Phase 4 path is `Playwright` + `Tavily` + `Tesseract` + `ADB`/`scrcpy` behind the router.
The shortest safe Phase 4.5 path is `mss`/`OpenCV` + `Tesseract` + `Vosk` + `pyttsx3` + `llama.cpp`.
The shortest safe Phase 5 path is `Chroma` or `Qdrant` plus `PEFT` + `LoRA` + `QLoRA` + `TRL`.

Machine execution rule: run only `X0` to `X4` on the current i5/16 GB machine, and queue heavy runs to `X5/X6` in `docs/PHASE_X_MACHINE_PLAN.md`.

Optional Phase 4 install commands (Windows-first):

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
winget install --id Google.PlatformTools -e --accept-package-agreements --accept-source-agreements
winget install --id Genymobile.scrcpy -e --accept-package-agreements --accept-source-agreements
```

Or use the project installer wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_system_deps.ps1
```

If you use Tavily live web search, set:

```powershell
$env:TAVILY_API_KEY = "<your_api_key>"
```

Quick checks:

```powershell
python -m playwright --version
tesseract --version
adb version
scrcpy --version
```

For a machine-local inventory of the active virtual environment, temp caches, downloaded models, external tools, URLs, and phase-to-resource mapping, see [RESOURCE_INVENTORY.md](RESOURCE_INVENTORY.md).
For tool-use safety, confirmation gates, audit logging, and local file/system protection rules, see [SECURITY_POLICY.md](SECURITY_POLICY.md).

To regenerate that inventory and refresh the package snapshot automatically on this machine, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/audit_resources.ps1
```

If you are touching export, evaluation, generation, or training resume code, keep checkpoint metadata as the source of truth first and use the shared loaders that already do this correctly.

### 📍 Audit Replay (Dry Run)

Use action audit replay to evaluate how current policy/router logic would handle historical requests without executing side effects.

```powershell
python scripts/replay_audit.py --input temp/action_audit.jsonl --output temp/benchmarks/audit_replay_report.json
```

Optional: force replay to treat all actions as confirmed (useful for "what-if" policy checks):

```powershell
python scripts/replay_audit.py --assume-confirmed
```

---

## 🛠️ Troubleshooting & Optimization

| Issue | Potential Solution |
| :--- | :--- |
| **High RAM pressure on i5 machine** | Keep `AI_LAN_EXP_PROFILE=transformer_small`, set `AI_LAN_BATCH_SIZE=8`, and defer heavy runs to `Phase X5/X6`. |
| **Loss is 'NaN'** | Ensure `AI_LAN_LEARNING_RATE` is not too high (e.g., 1e-4). |
| **Slow Training on CPU** | Reduce epochs and model size; keep `AI_LAN_USE_AMP='0'` for consistent CPU behavior. |
| **Generation is Repetitive** | Increase `AI_LAN_GENERATE_TEMPERATURE` (1.2+) or set `top_p=0.9`. |
| **FileNotFound in Tests** | Ensure your isolated test environment has established a `runs/` directory. |

---

*Developed by Nadeem Abbas | 🌌 AI Lan Project | [Phase 3.0 Stabilized & Phase 4.0 Ready]*
