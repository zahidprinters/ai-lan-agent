---
description: "Use when changing configuration, runtime workflow, scripts, or user-facing behavior. Ensures docs are updated in the same change and points to the right documentation files for config, architecture, API, and testing changes."
name: "Docs Sync For Config And Workflow Changes"
applyTo:
  - "docs/**/*.md"
  - "README.md"
  - "ROADMAP.md"
  - "CHANGELOG.md"
  - "config/**/*.yaml"
  - "training/config.py"
  - "runtime/**/*.py"
  - "api/**/*.py"
  - "scripts/**/*.py"
  - "main.ps1"
---
# Docs Sync Guidelines

- If behavior, configuration, command flow, or user-visible workflow changes, update docs in the same change.
- Prefer linking existing docs over duplicating long explanations.
- Keep docs changes minimal but complete: enough for users and agents to run and verify the updated behavior.
- Keep terminology consistent across docs (`router`, `safety`, `runtime`, `training`, `registry`) to avoid split-brain guidance.

## Mapping: Change Type To Docs

- Config key, environment variable, or defaults changed:
  - Update [../../docs/CONFIGURATION.md](../../docs/CONFIGURATION.md)
  - Update [../../README.md](../../README.md) if quick-start commands or defaults changed

- Runtime/session/chat/dashboard behavior changed:
  - Update [../../docs/USER_GUIDE.md](../../docs/USER_GUIDE.md)
  - Update [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) or [../../docs/PROJECT_STRUCTURE.md](../../docs/PROJECT_STRUCTURE.md) when flow boundaries changed
  - Update [../../README.md](../../README.md) when startup commands, endpoints, or usage steps changed

- API endpoint/request-response behavior changed:
  - Update [../../docs/API_REFERENCE.md](../../docs/API_REFERENCE.md)
  - Update [../../docs/USER_GUIDE.md](../../docs/USER_GUIDE.md) if user-facing API usage changed

- Testing workflow or validation expectations changed:
  - Update [../../docs/TESTING_GUIDELINES.md](../../docs/TESTING_GUIDELINES.md)

- Training/checkpoint/registry workflow changed:
  - Update [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md)
  - Update [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) if data flow or constraints changed
  - Update [../../README.md](../../README.md) if canonical commands changed

- Milestone, rollout, or current-state guidance changed:
  - Update [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md)
  - Update [../../ROADMAP.md](../../ROADMAP.md)
  - Update [../../CHANGELOG.md](../../CHANGELOG.md) for user-visible behavior changes

## Release Note Trigger

- Add a `CHANGELOG.md` entry when changes alter:
  - user commands or startup workflow,
  - API behavior or output format,
  - policy/confirmation behavior,
  - training checkpoint or promotion behavior.

## Documentation Quality Checks

- Keep command examples Windows-first and aligned with repository entrypoints.
- Keep commands consistent with virtual environment usage and test guidance.
- Verify file paths and command names exist in the workspace.
- When uncertain, add a short note in docs about limitations or pending follow-up instead of leaving silent drift.
- Keep docs synchronized with actual script entrypoints in `main.ps1` and `scripts/` wrappers.
