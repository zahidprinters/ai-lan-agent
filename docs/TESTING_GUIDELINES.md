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

## Storage Health And Cleanup Gate

- Storage telemetry and cleanup changes should include focused storage tests.
- Local command:
  - `python -m pytest tests/test_storage_health.py tests/test_dashboard_api.py tests/test_web_dashboard_shell.py -q --disable-warnings`
- Expected behavior: `/api/health` and `/api/state` include `storage` payload, `/api/storage` responds successfully, and cleanup dry-run reports candidate files without deleting by default.

## Eval Benchmark Gate

- Router/safety and benchmark-harness changes should run the strict benchmark gate before merge.
- To derive a case pack from historical audit traces first:
  - `python scripts/build_benchmark_cases_from_audit.py --input temp/action_audit.jsonl --output temp/benchmarks/trace_benchmark_cases.json --max-cases 25`
- Checked-in trace regression fixture:
  - `tests/fixtures/benchmarks/phase43_trace_cases.json`
- Local strict benchmark command:
  - `python scripts/benchmark_tools.py --output temp/benchmarks/local_tool_benchmark.json --cases tests/fixtures/benchmarks/phase43_depth_cases.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-error-rate 0.00 --max-latency-p95 2500 --required-category execution:1 --required-category confirmation:1 --required-category refusal:1 --min-category-match execution:0.90 --min-category-match confirmation:0.90 --min-category-match refusal:0.90 --required-distinct-actions execution:6 --required-distinct-actions confirmation:5 --required-distinct-actions refusal:2`
- Local strict trace-regression command:
  - `python scripts/benchmark_tools.py --output temp/benchmarks/checked_in_trace_tool_benchmark.json --cases tests/fixtures/benchmarks/phase43_trace_cases.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-error-rate 0.00 --max-latency-p95 2500 --required-category execution:1 --required-category confirmation:1 --required-category refusal:1 --min-category-match execution:0.90 --min-category-match confirmation:0.90 --min-category-match refusal:0.90 --required-distinct-actions execution:5 --required-distinct-actions confirmation:2 --required-distinct-actions refusal:1`
- Strict mode exits nonzero when any threshold fails.
- CI runs the curated benchmark gate when router/safety or benchmark harness files change, and optionally runs the checked-in trace fixture alongside it when trace-benchmark files or builder workflow files change.
- Use trace-derived case packs for local depth expansion when you want broader production-like request coverage without editing fixture JSON by hand.
- Category coverage assertions are part of the Phase 4.3 gate so benchmark packs cannot silently lose execution, confirmation, or refusal coverage.
- Per-category success thresholds are also part of the gate so a fixture cannot pass overall while one category degrades under the aggregate score.
- Distinct action diversity thresholds are part of the gate as well, so a category cannot satisfy coverage with a single repeated action shape.
