---
description: "Triage and fix a bug in this repo by reproducing it, narrowing scope, finding the root cause, adding or updating tests, and running the smallest useful validation. Use for failures in training, routing, runtime, checkpoints, summaries, or scripts."
name: "Bug Fix Triage"
argument-hint: "Describe the bug, failing behavior, traceback, or suspicious files."
agent: "agent"
---
Investigate and fix a bug in this repository.

Requirements:
- Start by identifying the narrowest reproducible failure from the user report, traceback, or affected files.
- Prefer the smallest root-cause fix over a surface patch.
- Preserve Windows-first, CPU-friendly behavior and keep temporary artifacts inside `temp/`.
- Respect repository conventions in [../../.github/copilot-instructions.md](../../.github/copilot-instructions.md), [../../docs/AI_GUIDELINES.md](../../docs/AI_GUIDELINES.md), and [../../docs/TESTING_GUIDELINES.md](../../docs/TESTING_GUIDELINES.md).
- If the bug touches checkpoints, run summaries, training metadata, router policy, or safety decisions, verify the related compatibility behavior rather than only the happy path.

Expected workflow:
1. Inspect the likely area and identify the minimal reproduction.
2. Confirm the failure with the smallest relevant command, test, or code-path inspection.
3. Trace the root cause through the responsible module instead of guessing.
4. Implement the smallest durable fix.
5. Add or update focused tests when feasible.
6. Run the smallest relevant validation, starting with unit tests.
7. Summarize the bug, root cause, fix, and what was verified.

Diagnosis checklist:
- Reproduction evidence:
	- exact failing test, stack trace, or deterministic code path.
- Root cause evidence:
	- concrete function or condition mismatch, not symptom-level description.
- Blast radius:
	- note whether fix affects only one layer or crosses router/safety/runtime/training.
- Regression coverage:
	- confirm the changed path has an automated assertion.

Output expectations:
- State the root cause clearly.
- State whether the issue was reproduced directly or inferred from code/tests.
- Mention any tests or commands run.
- Mention any residual risks or unverified paths.
- Include a one-line prevention note to reduce recurrence.