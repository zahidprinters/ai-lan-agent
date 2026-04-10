# Testing & Development Guidelines

- Always use the .venv virtual environment for all test, run, and development commands.
- Activate the environment before running any Python scripts or pytest:
  - On Windows PowerShell: `& .venv\Scripts\Activate.ps1`
  - On Unix/macOS: `source .venv/bin/activate`
- Run tests using the environment's Python:
  - `python -m pytest --maxfail=50 --disable-warnings -v`
- Do not use system Python or global pytest.
- All automation/scripts should assume .venv is present and active.
- Document this guideline in README and developer docs.

## Replay Gate

- Router and policy changes should be replay-validated with the dry-run audit gate before merge or release.
- Local strict replay command:
  - `python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict`
- Strict mode exits nonzero when replay finds diverged or skipped rows.
- The CI workflow runs the strict replay gate when router, safety, replay-script, or replay-fixture files change.

## Model Promotion Guardrail Gate

- Generate a quality artifact before promoting a candidate model through the registry CLI.
- Local artifact command:
  - `python scripts/benchmark_quality.py --model models/char_model.pt --version candidate-v1 --score 0.82`
- Local registry gate command:
  - `python scripts/model_registry.py --settings config/settings.yaml --quality-dir runs/quality activate --version candidate-v1`
- Activation exits nonzero when the quality artifact is missing, below `quality_guardrail_min_score`, or below the configured baseline model score.

## Dynamic Safety Gate

- Policy changes that affect confirmation behavior should include a dynamic-safety regression run.
- Local dynamic safety command:
  - `python -m pytest tests/test_dynamic_safety.py tests/test_policy_engine_config.py -q --disable-warnings`
- Sensitive context should require strong confirmation on selected risky actions, while non-sensitive context keeps existing behavior.

## Local-Brain Graceful Degradation Gate

- Planner backend fallback behavior should be regression-tested when touching `agents/react/controller.py` or `core/inference/local_reasoning.py`.
- Local fallback command:
  - `python -m pytest tests/test_local_reasoning.py tests/test_chat_interface.py tests/test_layered_modules.py -q --disable-warnings`
- Expected behavior: llama-cpp failures degrade immediately to classic planning and surface a debug-safe fallback reason in planner metadata.

## Dashboard Health Gate

- Dashboard/API health telemetry changes should include focused dashboard API tests.
- Local health dashboard command:
  - `python -m pytest tests/test_dashboard_api.py -q --disable-warnings`
- Expected behavior: `/api/state` includes `health` payload and `/api/health` reports CPU pressure proxy, RAM usage, and model confidence summary when available.

## Eval Benchmark Gate

- Router/safety and benchmark-harness changes should run the strict benchmark gate before merge.
- Local strict benchmark command:
  - `python scripts/benchmark_tools.py --output temp/benchmarks/local_tool_benchmark.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-latency-p95 2500`
- Strict mode exits nonzero when any threshold fails.
- CI runs this gate when router/safety or benchmark harness files change.
