---
description: "Use when writing or changing Python tests, pytest fixtures, assertions, or validation commands in this repo. Covers unit vs integration scope, .venv usage, temp handling, and sentinel-aware test practice."
name: "Python Tests"
applyTo: "tests/**/*.py"
---
# Python Test Guidelines

- Activate the workspace virtual environment before running Python or pytest commands: `& .venv\Scripts\Activate.ps1`.
- Prefer `python -m pytest` over bare `pytest` and start with the smallest relevant test target.
- Default to unit coverage first: `python -m pytest tests -m unit -q --disable-warnings`.
- Use broader validation only when the change warrants it: `python -m pytest tests -q --disable-warnings --ignore=tests/integration`.
- Treat integration tests as opt-in unless the task explicitly affects end-to-end behavior.
- Keep all test artifacts and temporary files inside `temp/`. Tests already redirect `TMP`, `TEMP`, and `TMPDIR` via [tests/conftest.py](../../tests/conftest.py).
- Preserve sentinel expectations. Tests assume `AI_LAN_DEBUG=1` by default, while trace/profile stay off unless a test opts in.
- Use `tmp_path`, fixtures, and monkeypatching instead of hardcoded user paths or system temp locations.
- When changing behavior that touches checkpoints, routing, safety, or run summaries, add or update the smallest focused regression test near the affected suite.
- Follow the broader testing and environment rules in [docs/TESTING_GUIDELINES.md](../../docs/TESTING_GUIDELINES.md) and [docs/AI_GUIDELINES.md](../../docs/AI_GUIDELINES.md).

## Test Selection Guide

- Pure utility or parser logic:
	- Run the nearest unit module first, then `tests -m unit`.
- Router or policy decisions:
	- Add accepted plus rejected or confirmation-required assertions.
- Checkpoint, summary, and registry behavior:
	- Include legacy schema and normalized schema coverage when applicable.
- Runtime/API behavior:
	- Prefer focused unit-level route or handler tests before broader suites.

## Assertion Quality

- Assert behavior and outputs, not implementation details that create brittle tests.
- Include explicit failure messages for complex assertions.
- Avoid over-broad mocks that hide policy, schema, or metadata regressions.

## Command Policy

- Preferred default after test edits:
	- `python -m pytest tests -m unit -q --disable-warnings`
- Preferred broader check before finishing larger changes:
	- `python -m pytest tests -q --disable-warnings --ignore=tests/integration`