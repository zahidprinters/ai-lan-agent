# AI Lan

AI Lan is a Windows-first, CPU-friendly language-model training and inference workspace built with Python and PyTorch.

The codebase is organized for practical experimentation: train locally, compare runs, export models, and validate behavior with automated tests.

As of 2026-04-06, the repository also includes a layered architecture scaffold for the agentic roadmap (`core/`, `agents/`, `memory/`, `safety/`, `router/`, `runtime/`, `learning/`, `api/`).

## Current Scope

- **Production Agency Core (Phase 4.5A):** GGUF runtime (`llama-cpp-python`) is the production reasoning path for local agent control, with CPU-first residency/fallback behavior.
- **Research/Training Core:** StackedTransformer-v2 remains the training and experimentation baseline under `training/`.
- **Neural Planner (ReAct):** Iterative multi-step reasoning using local transformers to plan actions (Thought -> Action -> Observation).
- **Hybrid Memory:** Vector-based retrieval (ChromaDB/FAISS) combined with keyword scoring for semantic context injection.
- **Vision Perception:** Screen capture and OCR (mss + Tesseract) for visual grounding and display analysis.
- **Hardware Mapping (i5 baseline):** AVX2-capable `llama-cpp-python` runtime with default `n_threads=4` for responsive CPU-only operation.
- **Adapter Maturity:** PC/Android adapters are intentionally constrained and policy-gated while broader side-effect coverage continues under planned adapter slices.

Machine-specific execution planning is documented in `docs/plans/PHASE_X_MACHINE_PLAN.md`.

### Legacy/Research Scope

- Character-level and BPE tokenization for baseline experiments.
- Multiple model families: bigram, char-MLP, transformer, LSTM, and GRU.
- Training utilities with warmup, early stopping, checkpoints, and run indexing.
- Checkpoint-aware export, evaluation, generation, and resume paths that recover config and tokenizer metadata from saved artifacts.
- Inference with temperature, top-k, top-p, and KV-cache generation paths.
- Deployment tools for ONNX export and dynamic quantization, with quantized checkpoints kept on the PyTorch inference path for now.
- Normalized run summaries and compatibility indexes for legacy and nested report schemas.
- Browser dashboard plus JSON state endpoints for route-based chat, overview, runs, models, memory, context, logs, ops, and health views.

## Project Layout

- `training/`: model training stack, configs, dataset, checkpoints, inference helpers.
- `training/models/`: architecture implementations.
- `tokenizer/`: char and BPE tokenizer implementations and factory loader.
- `core/`: model, inference, and quantization facades for the new architecture.
- `agents/`: ReAct logic, planning, and action execution layers.
- `memory/`: short-term, long-term, episodic, and summary memory scaffolding.
- `safety/`: policy, validation, sandbox, and confirmation facades.
- `router/`: action routing and schema interfaces.
- `scripts/`: evaluation, export, quantization, inference, and compatibility wrapper entry points.
- `scripts/ops/`: canonical operational maintenance scripts (resource audit and hardware profiling).
- `tests/`: unit and integration test suites.
- `docs/`: user, architecture, configuration, testing, and API documentation.
- `docs/plans/`: canonical planning documents for roadmap, machine lanes, and final-goal execution.
- `requirements/`: canonical dependency pin sets (`base.txt`, `dev.txt`) used by root compatibility wrappers.
- `models/gguf/`: local GGUF production models (for example Phi-4/Llama 8B quantized variants).

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
# Optional experiment tracking stack only when needed
python -m pip install .[experiment]
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

### Benchmark And Promote A Candidate Model

```powershell
python scripts/benchmark_quality.py --model models/char_model.pt --version candidate-v1 --score 0.82
python scripts/model_registry.py --settings config/settings.yaml --quality-dir runs/quality activate --version candidate-v1
```

The registry activation step enforces the quality benchmark artifact for the target version and blocks promotion if the score is missing, below the configured minimum, or below the configured baseline model.

### Run CLI Chat Interface

```powershell
python scripts/chat_cli.py
```

Unified launcher:

```powershell
python scripts/launch.py --mode cli
python scripts/launch.py --mode voice
python scripts/launch.py --mode web
python scripts/launch.py --mode api
python scripts/launch.py --mode companion   # API server surfaced as companion (port 8766)
python scripts/launch.py --mode satellite   # API server surfaced as satellite (port 8767)
python scripts/launch.py --mode api --profile work  # attach a named session profile
```

The legacy `main.py` demo entrypoint has been retired. Use `scripts/launch.py`, `scripts/chat_cli.py`, `scripts/chat_web.py`, or `main.ps1` for active workflows.

The chat interface supports natural tool commands (for example `search ...`, `context ...`, `list docs`, `system status`) and confirmation/session commands (`/confirm`, `/reject`, `/history`, `/save`, `/load`, `/last`, `/help`).
When neural planning is enabled, chat mode can also run a small bounded Thought -> Action -> Observation loop before replying, while still enforcing the same router, policy, and confirmation boundaries.
The planner prompt now uses a structured tool schema derived from the router registry, including arg contracts, confirmation hints, and risk labels.
Planner prompting for GGUF models follows a structured XML contract (`<thought>`, `<plan>`, `<action>`, `<reflection>`) to keep parser behavior deterministic across model families.
Planning is dynamic by complexity: simple actions can skip full multi-step plans, while higher-complexity tasks require explicit multi-step planning before tool execution.
The 4.5A foundation now routes GGUF requests through a dedicated inference manager with resident-model reuse, RAM-pressure unload fallback, and optional simple-versus-complex model selection.
The current 4.5A slice also validates model-supplied plans against 3 to 5 step quality checks, repairs weak plans with refusal-aware shaping when needed, compacts older turns/thoughts/observations before prompt growth gets unstable, and stops llama-cpp streaming early when an actionable tool trigger is complete.
Long-running sessions use rolling context with summarization instead of blunt truncation so older turns are compacted into memory blocks rather than dropped abruptly.
When perception is enabled, the latest screen/OCR snapshot is also injected into runtime context so the local planner can reason over live situational summaries.
The dashboard/API surfaces now expose that live perception summary, and CLI/voice chat shut down session resources cleanly on exit.
For lower machine load, runtime context assembly now applies a configurable section-size budget and perception sampling can adaptively back off when the screen state is unchanged.
Runtime telemetry should include agent reasoning traces (thought/plan/action/result/reflection) so planner quality can be debugged in real time.
Structured JSONL logs now default to `temp/logs/agent_reasoning.jsonl`, `temp/logs/tool_events.jsonl`, and `temp/logs/runtime_errors.jsonl`.
Planner-visible tool schema now includes richer risk metadata (`risk_tier`, `policy_mode`, `risk_reasons`) so risky or blocked actions can be shaped toward confirmation or refusal before dispatch.

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
The dashboard now uses a local `web/` shell with subpages such as `/overview`, `/chat`, `/runs`, `/models`, `/memory`, `/context`, `/logs`, `/ops`, and `/health`, all backed by the local JSON state API and local assets under `web/assets/`.

## Configuration

Runtime behavior is controlled by environment variables read in `training/config.py`.

Common examples:

- `AI_LAN_EXP_PROFILE=transformer_small`
- `AI_LAN_MODEL_TYPE=transformer`
- `AI_LAN_EPOCHS=50`
- `AI_LAN_BATCH_SIZE=8`
- `AI_LAN_DEVICE=cpu`
- `AI_LAN_REASONING_BACKEND=llama_cpp`
- `AI_LAN_LLAMACPP_MODEL_PROFILE=phi4_q4km`
- `AI_LAN_LLAMACPP_RESIDENT=1`
- `AI_LAN_REASONING_PLAN_STEPS_MIN=3`
- `AI_LAN_STREAM_TOOL_TRIGGER_ENABLED=1`

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full variable reference.

## Observability

The `@sentinel` decorator in `core/utils/debug.py` supports:

- entry/exit debug logs (`AI_LAN_DEBUG=1`)
- variable tracing (`AI_LAN_TRACE=1`)
- function profiling (`AI_LAN_PROFILE=1`)

See [docs/DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md).

Compatibility note: legacy imports from `debug_utils.py` and `_bootstrap.py` remain supported as thin wrappers while canonical implementations live under `core/utils/`.

## Dependency Groups

- Base runtime dependencies are canonically maintained in [requirements/base.txt](requirements/base.txt) and installed via [requirements.txt](requirements.txt).
- Development dependencies are canonically maintained in [requirements/dev.txt](requirements/dev.txt) and installed via [dev-requirements.txt](dev-requirements.txt).
- Optional experiment extras are declared in [pyproject.toml](pyproject.toml) under `project.optional-dependencies.experiment` and should be installed only when needed.
- Optional Phase 4 Python extras are declared in [pyproject.toml](pyproject.toml) under `project.optional-dependencies.phase4`.
- ONNX inference/export runtime is pinned in base dependencies (`onnxruntime==1.20.1`).
- ChromaDB is available as an optional local memory backend (`AI_LAN_MEMORY_BACKEND=chroma`) with automatic fallback to the built-in vector index when unavailable.

### System Dependency Installer

Install the Windows system binaries used by the current Phase 4 and 4.5 stack with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_system_deps.ps1
```

### Resource Audit

Regenerate the machine-local resource inventory and Python package snapshot with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/audit_resources.ps1
```

Compatibility wrapper (still supported):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/audit_resources.ps1
```

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

For Android side-effect actions in the current Phase 4.2 hardening slice, keep explicit allowlists even after enabling ADB writes:

```powershell
$env:AI_LAN_ANDROID_ALLOW_SIDE_EFFECTS = "1"
$env:AI_LAN_ANDROID_ALLOWED_PACKAGES = "com.android.settings,com.example.app"
$env:AI_LAN_ANDROID_ALLOWED_DEVICE_IDS = "emulator-5554"
```

With that guard in place, `android.launch_app` only targets listed packages, side-effect Android actions can be pinned to known device IDs, and screenshot outputs remain constrained to `temp/`.

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
- Archive-first cleanup is mandatory for anything old, unused, duplicate, extra, or no longer attached to the active project path.
- Move cleanup candidates into `archive/` instead of deleting them first.
- Use these archive buckets:
  - `archive/code/`
  - `archive/docs/`
  - `archive/assets/`
  - `archive/tools/`
  - `archive/tmp_snapshots/`
- Record every move in `archive/ARCHIVE_LOG.md`, including original path, archive path, date, reason, and restore notes.
- Keep active project code/features in the normal working tree; move stale temp downloads, debug leftovers, old snapshots, and retired compatibility material into `archive/` when they are no longer needed.

## Low-Bandwidth Prefetch

For slow or unstable internet, prefetch package and model/data assets to `temp/downloads`:

```powershell
python scripts/prefetch_low_bandwidth_assets.py --all-phases --with-model-assets --sync-runtime-paths
```

If you only want resumable model/data downloads (no pip wheel prefetch), use:

```powershell
python scripts/prefetch_low_bandwidth_assets.py --skip-packages --with-model-assets
```

To fetch a single HTTP asset (useful on very slow links), repeat `--asset` as needed:

```powershell
python scripts/prefetch_low_bandwidth_assets.py --skip-packages --with-model-assets --asset tinystories_text
```

This keeps offline-friendly caches for Phase 4/4.5/5 package wheels and key model/data downloads.

## Documentation Index

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- [docs/plans/ULTIMATE_JARVIS_MASTER_PLAN.md](docs/plans/ULTIMATE_JARVIS_MASTER_PLAN.md)
- [docs/RESOURCE_INVENTORY.md](docs/RESOURCE_INVENTORY.md)
- [docs/SECURITY_POLICY.md](docs/SECURITY_POLICY.md)
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

## Phase X Execution Lanes (Current Machine)

- Run now on i5/16GB: `X0` through `X4` in `docs/plans/PHASE_X_MACHINE_PLAN.md`.
- Defer to stronger hardware: `X5` and `X6` (heavy training/inference sweeps, long-horizon benchmarks, extended concurrency).

Audit command (machine-ready report):

```powershell
python scripts/phase_x_audit.py --strict
```

