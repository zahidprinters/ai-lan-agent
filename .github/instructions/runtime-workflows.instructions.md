---
description: "Use when editing runtime or API Python code. Enforces smoke-check plus targeted tests and keeps user-facing behavior, confirmation flow, and docs in sync."
name: "Runtime Workflows"
applyTo:
  - "runtime/**/*.py"
  - "api/**/*.py"
  - "scripts/launch.py"
---
# Runtime And API Workflow Guardrails

- Use this instruction only for runtime and API edits.
- Preserve Windows-first command examples and use repository entrypoints.
- Keep behavior changes minimal and explicit.
- Maintain compatibility with existing session lifecycle, confirmation flow, and router dispatch behavior.

## Required Validation

- Always run the PowerShell smoke check after runtime or API behavior changes:
  - `powershell -ExecutionPolicy Bypass -File main.ps1 check`
- Always run targeted tests for touched runtime/API behavior.
- If changes cross module boundaries, run the broader non-integration suite:
  - `python -m pytest tests -q --disable-warnings --ignore=tests/integration`

## Test Selection

- Runtime session/confirmation/chat flow:
  - `python -m pytest tests/test_chat_interface.py -q --disable-warnings`
- Dashboard/API route behavior:
  - `python -m pytest tests/test_dashboard_api.py -q --disable-warnings`
- Router-policy behavior touched via runtime/API path:
  - `python -m pytest tests/test_action_router.py tests/test_dynamic_safety.py -q --disable-warnings`

## Docs Sync Requirement

- If user-visible runtime workflow or API behavior changed, update docs in the same change.
- Link to existing docs instead of embedding long guidance:
  - `docs/USER_GUIDE.md`
  - `docs/API_REFERENCE.md`
  - `docs/ARCHITECTURE.md`
  - `docs/TESTING_GUIDELINES.md`

## Output Checklist

- State what behavior changed and where it is wired.
- List smoke check and targeted tests run.
- Note anything not verified and associated risk.
