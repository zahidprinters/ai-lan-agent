## Summary
Describe what changed and why.

## Related Work
Reference issue(s), roadmap item(s), or docs section(s).

## Scope
- [ ] No behavior change (refactor/docs/tests only)
- [ ] User-visible behavior changed
- [ ] Config/environment defaults changed
- [ ] Router/safety/policy behavior changed

## Risk Assessment
- [ ] Low (isolated module)
- [ ] Medium (cross-module)
- [ ] High (router/safety/runtime/training core)

If medium/high, describe rollback or mitigation plan:

## Validation Performed
Commands run and results:

```text
python -m pytest tests -m unit -q --disable-warnings
python -m pytest tests -q --disable-warnings --ignore=tests/integration
powershell -ExecutionPolicy Bypass -File main.ps1 check
```

## Router/Safety Checklist (if applicable)
- [ ] Confirmation-required path tested
- [ ] Rejection path tested
- [ ] `config/policies.yaml` and `safety/policy_engine.py` stay consistent
- [ ] Dry-run behavior validated (`dispatch_agent_action(..., dry_run=True)`)
- [ ] Audit replay impact validated (`python scripts/replay_audit.py`)

## Documentation Checklist
- [ ] Updated relevant docs (`README.md`, `docs/USER_GUIDE.md`, `docs/CONFIGURATION.md`, etc.)
- [ ] Added/updated `CHANGELOG.md` when user-visible behavior changed

## Final Checklist
- [ ] Code follows project style and typing conventions
- [ ] Tests added/updated for changed behavior
- [ ] No unrelated files included in this PR
