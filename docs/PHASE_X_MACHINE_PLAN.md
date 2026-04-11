# Phase X Machine Plan (i5 / 16 GB RAM)

This plan splits work into what should run now on the current machine and what should wait for a stronger machine.

## Current Machine Baseline

- CPU: Intel i5-8350U (4C/8T)
- RAM: 16 GB
- GPU: Integrated only (no CUDA)
- Mode: Windows-first, CPU-first, low-risk resource profile

Use this default environment for local work:

```powershell
$env:AI_LAN_DEVICE="cpu"
$env:AI_LAN_USE_AMP="0"
$env:AI_LAN_EXP_PROFILE="transformer_small"
$env:AI_LAN_BATCH_SIZE="8"
$env:AI_LAN_BLOCK_SIZE="16"
```

## Phase X0 - Stability Baseline (Do Now)

### X0 Goals

- Keep local development fast and deterministic.
- Prevent overheating, memory pressure, and unstable runs.

### X0 Scope Now

- Unit tests, router/safety tests, replay audit checks.
- Small benchmark slices and targeted regressions.
- Lightweight local-brain integration checks with graceful fallback.

### X0 Do Not Run Now

- Large dataset training jobs.
- Full multi-stack embodied loops for long durations.

### X0 Exit Gate

- All fast validation gates pass on this machine without resource spikes.

## Phase X1 - Reasoning Reliability First (Do Now)

### X1 Goals

- Improve planning, reflection, and tool routing quality before perception depth.

### X1 Scope Now

- ReAct planning depth and failure reflection tuning.
- Tool argument quality checks on small offline datasets.
- Deterministic replay coverage expansion.

### X1 Do Not Run Now

- Large-model sweeps or long-context stress runs.

### X1 Exit Gate

- Better tool success/refusal quality on local benchmark slices with stable latency.

## Phase X2 - Safety + Verification Expansion (Do Now)

### X2 Goals

- Make risky action control stricter and auditable.

### X2 Scope Now

- Policy confirmation-path coverage.
- State verification probes for side-effect actions.
- Audit log consistency and replay parity validation.

### X2 Do Not Run Now

- High-volume integration fuzzing.

### X2 Exit Gate

- Confirmation-required and reject-path tests pass consistently.

## Phase X3 - Embodied Lite (Do Now, Narrow Scope)

### X3 Goals

- Build minimal CPU-safe perception loop without deep model load.

### X3 Scope Now

- Screenshot + OCR pipeline in bounded intervals.
- Lightweight voice I/O smoke tests only.
- Health telemetry checks for RAM/latency pressure.

### X3 Do Not Run Now

- Continuous real-time perception loops at production cadence.

### X3 Exit Gate

- Short embodied demo works with bounded latency and safety gates intact.

## Phase X4 - Heavy-Machine Readiness (Do Now)

### X4 Goals

- Prepare everything required so migration is mostly a switch-over.

### X4 Scope Now

- Finalize configs, scripts, policies, and benchmark thresholds.
- Keep model artifacts versioned and registry-safe.
- Document exact runbooks for heavy-machine execution.

### X4 Deliverables

- Reproducible command set for heavy runs.
- Clear pass/fail thresholds and promotion gates.

### X4 Exit Gate

- Zero unknowns remain for heavy-machine rollout.

## Phase X5 - Heavy-Machine Execution (Defer)

Run only when stronger hardware is available.

### X5 Scope Deferred

- Larger model inference/training sweeps.
- Long-horizon benchmark datasets.
- Extended embodied concurrency tests.
- Promotion candidates requiring bigger compute windows.

### X5 Exit Gate

- Candidate model passes benchmark, latency, and safety thresholds.

## Phase X6 - Promotion + Continuous Ops (Defer)

### X6 Scope Deferred

- Nightly larger-scale evaluation and learning loops.
- Automated promotion/rollback operations with broader datasets.

### X6 Exit Gate

- Stable multi-run quality with no safety regressions.

## Weekly Execution Rhythm (Current i5 Machine)

- 3 days: feature work in reasoning/safety/router layers.
- 1 day: targeted benchmark + replay regression.
- 1 day: docs sync + stabilization + cleanup.

## Command Set For Current Machine

```powershell
# one-shot phase audit report (X0/X1/X2 gates)
python scripts/phase_x_audit.py --strict

# fast unit scope
python -m pytest tests -m unit -q --disable-warnings

# non-integration broad pass
python -m pytest tests -q --disable-warnings --ignore=tests/integration

# policy and safety checks
python -m pytest tests/test_dynamic_safety.py tests/test_policy_engine_config.py -q --disable-warnings

# local-brain graceful fallback checks
python -m pytest tests/test_local_reasoning.py tests/test_chat_interface.py tests/test_layered_modules.py -q --disable-warnings

# replay gate
python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict
```

## Decision Rule

- If a task can pass in under 20 minutes and under safe RAM pressure on i5, run now.
- If it needs long-running high-memory jobs or broad concurrency stress, queue to Phase X5.
