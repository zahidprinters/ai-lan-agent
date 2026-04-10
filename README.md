# AI Lan

AI Lan is a Windows-first, CPU-friendly language-model training and inference workspace built with Python and PyTorch.

The codebase is organized for practical experimentation: train locally, compare runs, export models, and validate behavior with automated tests.

As of 2026-04-06, the repository also includes a layered architecture scaffold for the agentic roadmap (`core/`, `agents/`, `memory/`, `safety/`, `router/`, `runtime/`, `learning/`, `api/`).

## Current Scope

- **Neural Planner (ReAct):** Iterative multi-step reasoning using local transformers to plan actions (Thought -> Action -> Observation).
- **Hybrid Memory:** Vector-based retrieval (ChromaDB/FAISS) combined with keyword scoring for semantic context injection.
- **Vision Perception:** Screen capture and OCR (mss + Tesseract) for visual grounding and display analysis.
- Character-level and BPE tokenization.
- Multiple model families: bigram, char-MLP, transformer, LSTM, and GRU.
- Training utilities with warmup, early stopping, checkpoints, and run indexing.
- Checkpoint-aware export, evaluation, generation, and resume paths that recover config and tokenizer metadata from saved artifacts.
- Inference with temperature, top-k, top-p, and KV-cache generation paths.
- Deployment tools for ONNX export and dynamic quantization, with quantized checkpoints kept on the PyTorch inference path for now.
- Normalized run summaries and compatibility indexes for legacy and nested report schemas.
- Browser dashboard plus JSON state endpoints for route-based chat, overview, runs, models, memory, context, logs, and ops views.

## Project Layout

- `training/`: model training stack, configs, dataset, checkpoints, inference helpers.
- `training/models/`: architecture implementations.
- `tokenizer/`: char and BPE tokenizer implementations and factory loader.
- `core/`: model, inference, and quantization facades for the new architecture.
- `agents/`: ReAct logic, planning, and action execution layers.
- `memory/`: short-term, long-term, episodic, and summary memory scaffolding.
- `safety/`: policy, validation, sandbox, and confirmation facades.
- `router/`: action routing and schema interfaces.
- `scripts/`: evaluation, export, quantization, and inference entry points.
- `tests/`: unit and integration test suites.
- `docs/`: user, architecture, configuration, testing, and API documentation.

## Quick Start

1. Create and activate the virtual environment.
2. Install dependencies.
3. Run training or generation.

```powershell
# From repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r dev-requirements.txt
```

### Train

```powershell
python training/train_char_model.py
```

### Generate

```powershell
python training/generate.py
```

### Run Unit Tests

```powershell
python -m pytest tests -q --disable-warnings --ignore=tests/integration
```

### Run Layered Runtime Demo

```powershell
python main.py
```

### Run CLI Chat Interface

```powershell
python scripts/chat_cli.py
```

Unified launcher:

```powershell
python scripts/launch.py --mode cli
python scripts/launch.py --mode web
python scripts/launch.py --mode api
```

The chat interface supports natural tool commands (for example `search ...`, `context ...`, `list docs`, `system status`) and confirmation/session commands (`/confirm`, `/reject`, `/history`, `/save`, `/load`, `/last`, `/help`).

### Run CLI Dashboard

```powershell
powershell -ExecutionPolicy Bypass -File main.ps1 dashboard
```

The PowerShell dashboard now groups actions into Workspace, Training, Knowledge, System, Quality, and System Config sections, with local Knowledge/System views for models, memory, context, logs, and ops.

For direct local views, run `python scripts/dashboard_views.py models`, `memory`, `context`, `logs`, or `ops`.

### Run Web Chat Interface

```powershell
python scripts/chat_web.py
```

Then open `http://127.0.0.1:8765/overview` in your browser.
The dashboard now uses a local `web/` shell with subpages such as `/overview`, `/chat`, `/runs`, `/models`, `/memory`, `/context`, `/logs`, and `/ops`, all backed by the local JSON state API and local assets under `web/assets/`.

## Configuration

Runtime behavior is controlled by environment variables read in `training/config.py`.

Common examples:

- `AI_LAN_EXP_PROFILE=debug`
- `AI_LAN_MODEL_TYPE=transformer`
- `AI_LAN_EPOCHS=50`
- `AI_LAN_BATCH_SIZE=32`
- `AI_LAN_DEVICE=cpu`

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full variable reference.

## Observability

The `@sentinel` decorator in `debug_utils.py` supports:

- entry/exit debug logs (`AI_LAN_DEBUG=1`)
- variable tracing (`AI_LAN_TRACE=1`)
- function profiling (`AI_LAN_PROFILE=1`)

See [docs/DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md).

## Dependency Groups

- Base runtime dependencies are in [requirements.txt](requirements.txt).
- Development and optional experiment tracking dependencies are in [dev-requirements.txt](dev-requirements.txt).
- Optional experiment extras are declared in [pyproject.toml](pyproject.toml) under `project.optional-dependencies.experiment`.
- Optional Phase 4 Python extras are declared in [pyproject.toml](pyproject.toml) under `project.optional-dependencies.phase4`.
- ONNX inference/export runtime is pinned in base dependencies (`onnxruntime==1.20.1`).

### Optional Phase 4 Setup (Windows)

This is the shortest safe stack from `docs/OPEN_SOURCE_REFERENCE.md`: Playwright + Tavily + Tesseract + ADB/scrcpy.

```powershell
# Python packages (already pinned in requirements.txt)
python -m pip install -r requirements.txt

# Playwright browser runtime
python -m playwright install chromium

# System tools
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
winget install --id Google.PlatformTools -e --accept-package-agreements --accept-source-agreements
winget install --id Genymobile.scrcpy -e --accept-package-agreements --accept-source-agreements
```

Optional search key (needed only for live Tavily search APIs):

```powershell
$env:TAVILY_API_KEY = "<your_api_key>"
```

Quick verification:

```powershell
python -m playwright --version
tesseract --version
adb version
scrcpy --version
```

## Workspace Cleanliness Policy

- Temporary files and generated caches should stay inside `temp/`.
- Model/run outputs belong in `models/` and `runs/`.
- Do not commit transient cache folders such as `__pycache__/`.

## Documentation Index

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md)
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- [docs/TESTING_GUIDELINES.md](docs/TESTING_GUIDELINES.md)
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- [docs/HARDWARE_PROFILE.md](docs/HARDWARE_PROFILE.md)
- [ROADMAP.md](ROADMAP.md)

## External Reference Stack

The curated upstream source list for Phase 4 and Phase 5 work lives in [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md).
Use that guide before adding new third-party agent, training, browser, perception, memory, or learning dependencies.
Start with one project per capability: agent framework, browser stack, search stack, OCR stack, Android stack, memory backend, finetuning stack, dataset pipeline, orchestration layer, and home automation target.
The next embodied slice is CPU-first vision + voice + local reasoning: `mss`/`OpenCV`, `Tesseract`, `Vosk`, `pyttsx3`, and `llama.cpp`.
If you want a skills-app reference for voice commands and reusable plugins, start with `OpenVoiceOS`.
