---
description: "Run a release-readiness check before model promotion. Use for candidate validation, checkpoint and summary compatibility checks, registry guard review, rollback readiness, and docs sync confirmation."
name: "Release Readiness For Model Promotion"
argument-hint: "Provide candidate model path/version, target registry entry, and any known risks or failing signals."
agent: "agent"
---
Perform a release-readiness review for model promotion in this repository.

Scope:
- Candidate checkpoint and metadata health.
- Run-summary compatibility (legacy flat and nested schemas).
- Registry promotion safety (activation and rollback readiness).
- Validation coverage and residual risk.
- Documentation/config sync for any changed behavior.

Required checks:
1. Confirm the candidate is a real artifact and not a placeholder.
2. Verify checkpoint metadata is sufficient for downstream workflows and treated as source of truth.
3. Verify run-summary normalization assumptions still hold for reporting and indexing paths.
4. Confirm quantization or export constraints are respected for this candidate.
5. Confirm model-registry promotion and rollback paths remain valid.
6. Confirm the smallest relevant tests or validations were run, and clearly state what was not run.
7. Confirm docs and config references are aligned for any changed workflow.

Evidence expectations per check:
- Artifact validity:
	- model path/version and why it is a non-placeholder candidate.
- Metadata:
	- checkpoint config/tokenizer fields required by downstream paths.
- Summary compatibility:
	- explicit note for legacy flat and nested summary support.
- Registry safety:
	- activation and rollback readiness with expected payload behavior.
- Validation:
	- exact commands or test groups used and result status.
- Docs sync:
	- list of updated docs or explicit statement that no docs changes were required.

Output format:
- Decision: Ready, Ready with Conditions, or Not Ready.
- Evidence: concise bullet list of what was validated.
- Risks: concise bullet list of remaining blockers or unknowns.
- Required follow-ups: exact files/tests/commands to complete before promotion.
- Promotion gate summary: one line with the top reason for the decision.

Repository references:
- [../../training/checkpoints.py](../../training/checkpoints.py)
- [../../training/model_registry.py](../../training/model_registry.py)
- [../../scripts/model_registry.py](../../scripts/model_registry.py)
- [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md)
- [../../docs/CONFIGURATION.md](../../docs/CONFIGURATION.md)
- [../../docs/TESTING_GUIDELINES.md](../../docs/TESTING_GUIDELINES.md)
