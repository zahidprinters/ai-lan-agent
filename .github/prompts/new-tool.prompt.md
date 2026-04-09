---
description: "Scaffold or update a repo-native tool or action workflow with schema, policy, registration, tests, and docs. Use for new router actions, tool stubs, safe integrations, or dispatch-path extensions."
name: "New Tool Workflow"
argument-hint: "Describe the capability to add, where it should live, and whether it is read-only, confirmation-gated, or state-changing."
agent: "agent"
---
Create or update a repository-native tool or action workflow for this workspace.

Requirements:
- Follow the repo's layered boundaries from [docs/PROJECT_STRUCTURE.md](../../docs/PROJECT_STRUCTURE.md) and [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).
- Use the flow from [docs/AI_GUIDELINES.md](../../docs/AI_GUIDELINES.md): schema first, then policy/confirmation behavior, then a safe stub or implementation, then registration, then tests.
- Preserve Windows-first, CPU-friendly behavior and keep temporary artifacts in `temp/`.
- Prefer minimal changes and preserve compatibility with both the newer layered scaffold and any active legacy path.
- Keep policy behavior explicit: state whether the new action is allowed, denied, or confirmation-required.

Expected workflow:
1. Inspect the existing router, schema, policy, and tool registration surfaces relevant to the requested capability.
2. Identify the smallest safe design that satisfies the request.
3. Implement the change end-to-end where feasible, including tests and any necessary docs updates.
4. Run the smallest relevant validation commands, starting with unit tests.
5. Summarize the user-facing behavior, safety posture, and files changed.

Implementation checklist:
- Schema:
	- Action name and argument shape are explicit and validated.
- Policy:
	- Confirmation or denial behavior is intentional and testable.
- Dispatch:
	- Registration path is clear and compatibility with legacy path is preserved.
- Tool path:
	- Initial implementation is safe-by-default with deterministic failure output.
- Validation:
	- Added or updated tests cover successful and blocked/denied cases where relevant.
- Docs:
	- Config, workflow, or API docs updated when behavior changed.

Output expectations:
- State where the capability was wired.
- State whether it is read-only, confirmation-required, or blocked by policy.
- Mention which validation commands were run and anything not verified.
- Include a short risk note for any unverified integration path.