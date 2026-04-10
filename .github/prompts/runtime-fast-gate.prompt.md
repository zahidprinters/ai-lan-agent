---
description: "Run a fast runtime/API validation workflow: smoke check plus targeted tests, with optional broader suite when changes cross module boundaries."
name: "Runtime Fast Gate"
argument-hint: "Describe the runtime or API change and which user-facing behavior should be validated."
agent: "agent"
---
Implement and validate a runtime/API change with a fast, practical gate.

Scope:
- Runtime and API behavior in `runtime/**/*.py`, `api/**/*.py`, and launch flow in `scripts/launch.py`.

Required workflow:
1. Inspect touched runtime/API files and identify user-visible behavior changes.
2. Implement the minimal safe change.
3. Run smoke check:
   - `powershell -ExecutionPolicy Bypass -File main.ps1 check`
4. Run targeted tests based on touched behavior:
   - Chat/session/confirmation flow:
     - `python -m pytest tests/test_chat_interface.py -q --disable-warnings`
   - Dashboard/API route behavior:
     - `python -m pytest tests/test_dashboard_api.py -q --disable-warnings`
   - Runtime path touching router/safety outcomes:
     - `python -m pytest tests/test_action_router.py tests/test_dynamic_safety.py -q --disable-warnings`
5. If the change crosses module boundaries or has broad side effects, run:
   - `python -m pytest tests -q --disable-warnings --ignore=tests/integration`
6. If behavior is user-visible or contract-level, update docs in the same change:
   - `docs/USER_GUIDE.md`
   - `docs/API_REFERENCE.md`
   - `docs/TESTING_GUIDELINES.md`

Final response requirements:
- Summarize behavior change and affected files.
- List smoke check and test commands run.
- Note any unverified paths and residual risk.
