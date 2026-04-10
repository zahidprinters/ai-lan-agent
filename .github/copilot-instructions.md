# Project Guidelines

## Code Style
- This is a Windows-first, CPU-friendly Python 3.11+ workspace. Use the project virtual environment for all Python, pytest, and script commands: `& .venv\Scripts\Activate.ps1`.
- Prefer `python -m ...` or the repository's PowerShell/Python entrypoints over global tools.
- Keep changes consistent with `.editorconfig` and the existing `black` configuration in `pyproject.toml` (line length 100).
- Add type hints to new or changed Python functions. Preserve `@sentinel` coverage on major logic paths and use the shared observability flow instead of ad hoc debug code.
- Favor compatibility-first changes: keep wrapper entrypoints in `scripts/` aligned with implementation modules in `training/`, `runtime/`, `router/`, and `safety/`.

## Architecture
- Treat the repository as a layered system: `agents/` handles reasoning, `router/` handles action dispatch, `safety/` handles policy decisions, `memory/` handles retrieval/state, `runtime/` exposes user-facing session surfaces, and `training/` remains the stable model/training path.
- The newer layered scaffold coexists with legacy paths under `tools/`, `training/`, and `scripts/`. Extend incrementally and preserve compatibility instead of assuming Phase 4 is fully wired.
- Follow the separation documented in `docs/PROJECT_STRUCTURE.md` and `docs/ARCHITECTURE.md`: agents think, tools act, memory remembers, safety controls.
- Route behavior changes through the owning layer rather than cross-layer shortcuts (for example, avoid embedding policy logic in tool execution code).

## Current Phase Status
- Phase 4.1 safety freeze behavior is active: router dispatch is schema-validated, policy-gated, and audit-logged.
- Policy sets are runtime-loaded from `config/policies.yaml` (allow/deny/require_confirmation) with safe fallback defaults in `safety/policy_engine.py`.
- Optional Phase 4 stack is integrated behind facades: Playwright + Tavily + Tesseract + ADB/scrcpy.
- Audit replay is available via `scripts/replay_audit.py` and router dry-run mode (`dispatch_agent_action(..., dry_run=True)`) for side-effect-free policy evaluation.
- Sentinel trace output now sanitizes sensitive values before logging; preserve this behavior when changing observability code.

## Build and Test
- Default fast validation: `python -m pytest tests -m unit -q --disable-warnings`.
- Broader validation before finishing larger changes: `python -m pytest tests -q --disable-warnings --ignore=tests/integration`.
- PowerShell smoke check: `powershell -ExecutionPolicy Bypass -File main.ps1 check`.
- Router and policy regression gate: `python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict`.
- Treat integration tests, model training, export/quantization, and interactive CLI/web/API launch commands as non-default workflows unless the task requires them.
- Validation ladder for typical edits:
	- Small local fix: unit target for affected area.
	- Cross-module change: full non-integration suite.
	- Runtime/API workflow changes: include smoke check plus targeted tests.

## Conventions
- Keep temporary files, caches, and generated scratch data inside `temp/`. Do not introduce hardcoded user-profile paths or system temp usage; tests already redirect temp via `tests/conftest.py`.
- Prefer script entrypoints over ad hoc invocation: `main.ps1` for Windows orchestration and `scripts/launch.py` for runtime mode switching.
- For new tool or action work, follow the project flow in `docs/AI_GUIDELINES.md`: define schema, define policy/confirmation behavior, implement a safe stub first, register it, then add tests.
- Use shared checkpoint and run-summary helpers in `training/checkpoints.py` for resume, export, evaluation, generation, and indexing work. Checkpoint metadata is the source of truth, and run summaries may need normalization.
- Before adding new external dependencies or capability stacks, consult `docs/OPEN_SOURCE_REFERENCE.md` and keep integrations behind local facades.
- Preserve auditability for behavior changes: prefer explicit validation/error paths and avoid silent fallbacks that hide policy or metadata failures.
- Treat model promotion and rollback as guarded workflows; avoid manual registry edits when helper APIs already exist.

## Common Pitfalls
- `.venv` not active: activate with `& .venv\Scripts\Activate.ps1` before any Python or pytest command.
- Temp leakage: route all temporary and cache outputs to `temp/`, not system temp or user-profile paths.
- Layer bypass: avoid implementing policy logic inside tools; route through `router/` and `safety/` ownership.
- Shim edits: prefer changing owning implementations over compatibility shims unless the task is explicitly about migration wiring.

## High-Risk Areas
- `router/`, `safety/`: policy, confirmation, and dispatch correctness.
- `scripts/replay_audit.py`: audit decision replay correctness and deterministic comparison logic.
- `training/checkpoints.py`, `training/model_registry.py`, `scripts/model_registry.py`: artifact metadata, normalization, and promotion safety.
- `runtime/`, `api/`, `scripts/launch.py`: user-facing workflow and route behavior.
- `config/` and `training/config.py`: environment and default behavior drift.

## Change Checklist
- Keep `.venv` active for all Python actions.
- Make the minimal code change that fixes the root issue.
- Add/update targeted tests when behavior changes.
- Run the smallest relevant validation commands.
- Update docs in the same change when config, workflow, API, or user-visible behavior changes.
- For router/safety changes, include at least one confirmation-required and one rejection-path assertion.
- For policy changes, verify `config/policies.yaml` and `safety/policy_engine.py` remain consistent.
- For audit replay/dry-run changes, add tests under `tests/test_audit_replay.py`.

## Reference Docs
- Read `docs/AI_CONTEXT.md` for current roadmap and handoff context.
- Read `docs/AI_GUIDELINES.md` for repository-specific development rules.
- Read `docs/CONFIGURATION.md` for environment variables and runtime settings.
- Read `docs/TESTING_GUIDELINES.md` for test execution expectations.
- Read `docs/API_REFERENCE.md` for API contracts and route behavior.
- Read `docs/USER_GUIDE.md` for runtime and chat/dashboard usage expectations.

## Docs Map (Link, Don't Embed)
- Architecture and boundaries: `docs/ARCHITECTURE.md`, `docs/PROJECT_STRUCTURE.md`, `docs/AGENCY_MAP.md`.
- Runtime and operations: `docs/USER_GUIDE.md`, `docs/DEBUGGING_GUIDE.md`, `docs/RESOURCE_INVENTORY.md`.
- Configuration and safety: `docs/CONFIGURATION.md`, `docs/SECURITY_POLICY.md`, `config/policies.yaml`.
- Testing and validation gates: `docs/TESTING_GUIDELINES.md`.
- Training and registry workflows: `docs/AI_CONTEXT.md`, `training/checkpoints.py`, `training/model_registry.py`.