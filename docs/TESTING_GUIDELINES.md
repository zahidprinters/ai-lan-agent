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
- Expected behavior: llama-cpp failures degrade immediately to classic planning when no candidate can succeed, preferred GGUF candidates can fall back to secondary routed candidates first, and planner metadata surfaces the selected route plus debug-safe fallback reasons.

## Phase 4.5A Planning / Streaming Gate

- When touching `core/inference/engine.py`, `agents/react/planner.py`, `agents/react/reflection.py`, `agents/react/agent.py`, or the prompt compaction path, run the focused 4.5A gate first.
- Local command:
  - `python -m pytest tests/test_inference_manager.py tests/test_local_reasoning.py tests/test_layered_modules.py tests/test_iterative_react.py tests/test_chat_interface.py -q --disable-warnings`
- Expected behavior: planner metadata carries a validated or repaired 3-5 step plan, stream interception can orchestrate JSON or text-based tool triggers, execution-contract checks block payload drift before dispatch, older prompt state is compacted into role-aware summaries with preserved runtime-context edges, richer risk metadata appears in planner/log records, reflection decisions are explicit, and structured logs are emitted for agent/tool/error paths.

## Phase 4.5B Perception Runtime Gate

- When touching `tools/perception/ocr.py`, `tools/perception/vision.py`, `runtime/perception_loop.py`, `runtime/context.py`, or runtime chat perception wiring, run the focused 4.5B gate before merge.
- Local command:
  - `python -m pytest tests/test_phase4_tools.py tests/test_perception_loop.py tests/test_chat_interface.py tests/test_vision_tool.py -q --disable-warnings`
- Expected behavior: bounded perception sampling stays in range, OCR confidence filtering remains active, unsupported backend selection fails safely, backend/fallback/preprocess controls propagate through perception loop wiring, and runtime context includes perception source/confidence/backend metadata.

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
  - `python scripts/benchmark_tools.py --output temp/benchmarks/local_tool_benchmark.json --cases tests/fixtures/benchmarks/phase43_depth_cases.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-error-rate 0.00 --max-latency-p95 2500 --min-runtime-guard-match 1.00 --min-execution-contract-match 1.00 --min-routing-assertion-match 1.00 --min-compaction-assertion-match 1.00 --required-category execution:1 --required-category confirmation:1 --required-category refusal:1 --required-category orchestration:1 --min-category-match execution:0.90 --min-category-match confirmation:0.90 --min-category-match refusal:0.90 --min-category-match orchestration:0.90 --required-distinct-actions execution:6 --required-distinct-actions confirmation:5 --required-distinct-actions refusal:2 --required-distinct-actions orchestration:3`
- Local strict trace-regression command:
  - `python scripts/benchmark_tools.py --output temp/benchmarks/checked_in_trace_tool_benchmark.json --cases tests/fixtures/benchmarks/phase43_trace_cases.json --strict --min-tool-success 0.66 --min-refusal-quality 0.90 --max-error-rate 0.00 --max-latency-p95 2500 --min-runtime-guard-match 1.00 --min-execution-contract-match 1.00 --min-routing-assertion-match 1.00 --min-compaction-assertion-match 1.00 --required-category execution:1 --required-category confirmation:1 --required-category refusal:1 --required-category orchestration:1 --min-category-match execution:0.90 --min-category-match confirmation:0.90 --min-category-match refusal:0.90 --min-category-match orchestration:0.90 --required-distinct-actions execution:5 --required-distinct-actions confirmation:2 --required-distinct-actions refusal:1 --required-distinct-actions orchestration:1`
- Strict mode exits nonzero when any threshold fails.
- CI runs the curated benchmark gate when router/safety or benchmark harness files change, and optionally runs the checked-in trace fixture alongside it when trace-benchmark files or builder workflow files change.
- Use trace-derived case packs for local depth expansion when you want broader production-like request coverage without editing fixture JSON by hand.
- Category coverage assertions are part of the Phase 4.3 gate so benchmark packs cannot silently lose execution, confirmation, or refusal coverage.
- Per-category success thresholds are also part of the gate so a fixture cannot pass overall while one category degrades under the aggregate score.
- Distinct action diversity thresholds are part of the gate as well, so a category cannot satisfy coverage with a single repeated action shape.
- Runtime guard alignment is part of the gate: orchestration cases now assert `expected_guard_allowed`, and strict runs fail when `runtime_guard_decision_match_rate` drops below threshold.
- Phase 4.5A hardening probes are part of the curated depth gate: cases can now assert `expected_execution_contract_valid`, attach a `routing_probe`, and attach a `compaction_probe`, with strict runs failing if `execution_contract_match_rate`, `routing_assertion_match_rate`, or `compaction_assertion_match_rate` regresses.
- Benchmark reports now include a compact `probe_failures` summary section (evaluated count, failed count, first failed case names, and reason histogram when available) to speed CI triage.
