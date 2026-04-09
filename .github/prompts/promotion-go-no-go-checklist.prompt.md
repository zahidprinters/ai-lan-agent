---
description: "Compact single-screen promotion checklist for fast go/no-go decisions before model promotion. Use when you need a quick readiness verdict with minimal output."
name: "Promotion Go No-Go Checklist"
argument-hint: "Provide candidate model path/version and any known risks or failing checks."
agent: "agent"
---
Run a compact pre-promotion checklist and return a single-screen decision.

Checklist (mark each as PASS, FAIL, or UNKNOWN):
1. Candidate artifact exists and is not a placeholder.
2. Checkpoint metadata is complete enough for load/eval/export or clearly bounded.
3. Run-summary compatibility is intact (legacy flat and nested schemas handled).
4. Registry actions are safe (promotion, activation, rollback path available).
5. Quantization or export constraints are respected for this candidate.
6. Required validation was run (at minimum, relevant unit coverage) and results are clear.
7. Docs/config impact is synced where behavior or workflow changed.

Output format (single-screen only):
- Decision: GO or NO-GO
- Score: X/7 PASS
- Fails: short comma-separated list (or `none`)
- Unknowns: short comma-separated list (or `none`)
- Next actions: up to 3 short actions
- Confidence: High, Medium, or Low

Rules:
- Keep output under 15 lines.
- Prefer direct evidence from repository files, tests, and known command results.
- If evidence is missing, mark UNKNOWN rather than assuming PASS.
- If any mandatory safety or rollback check fails, force NO-GO regardless of total score.

References:
- [../../training/checkpoints.py](../../training/checkpoints.py)
- [../../training/model_registry.py](../../training/model_registry.py)
- [../../scripts/model_registry.py](../../scripts/model_registry.py)
- [../../docs/CONFIGURATION.md](../../docs/CONFIGURATION.md)
- [../../docs/TESTING_GUIDELINES.md](../../docs/TESTING_GUIDELINES.md)
- [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md)
