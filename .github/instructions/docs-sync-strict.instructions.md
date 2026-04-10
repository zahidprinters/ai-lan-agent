---
description: "Use when config, workflow, or user-facing behavior changes. Requires same-change documentation updates with an explicit doc-update checklist."
name: "Docs Sync Strict"
applyTo:
  - "docs/**/*.md"
  - "config/**/*.yaml"
  - "runtime/**/*.py"
  - "api/**/*.py"
---
# Strict Docs Sync

- Any config, workflow, API contract, or user-visible behavior change must include documentation updates in the same change.
- Prefer linking canonical docs rather than duplicating explanations.
- Keep docs concise, accurate, and Windows-first for commands.

## Required Doc-Update Checklist

- Confirm whether behavior changed in any of these categories:
  - configuration keys/defaults
  - runtime or session flow
  - API request/response behavior
  - testing/validation workflow
  - policy/confirmation behavior
- Update all relevant docs before considering the task complete.

## Mapping

- Configuration changes:
  - `docs/CONFIGURATION.md`
  - `README.md` when quick-start/defaults changed
- Runtime and user workflow changes:
  - `docs/USER_GUIDE.md`
  - `docs/ARCHITECTURE.md` or `docs/PROJECT_STRUCTURE.md` when flow boundaries changed
- API behavior changes:
  - `docs/API_REFERENCE.md`
  - `docs/USER_GUIDE.md` for user-facing API usage
- Testing workflow changes:
  - `docs/TESTING_GUIDELINES.md`
- Safety and policy behavior changes:
  - `docs/SECURITY_POLICY.md`
  - `config/policies.yaml`
- User-visible release-impacting changes:
  - `CHANGELOG.md`

## Completion Gate

Do not finish the task until all apply-to docs are updated or explicitly confirmed as unchanged.

Report at completion:
- Which docs were updated.
- Why each updated doc was necessary.
- Any intentional doc omissions and rationale.
