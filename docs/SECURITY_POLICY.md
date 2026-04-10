# AI Lan Security Policy

Last updated: 2026-04-10

## Purpose

This document describes how AI Lan protects the local machine while the project evolves from a training workspace into a tool-using agent.

The current security model is based on:

- schema validation before execution,
- allow and deny policy enforcement,
- confirmation gates for higher-risk actions,
- audit logging for every action request and result,
- safe stub behavior for adapters that are not yet fully trusted,
- Windows-first local execution with explicit operator control.

## Current Security Boundaries

AI Lan separates responsibilities across layers:

- `agents/` decide what to request.
- `router/` validates and dispatches actions.
- `safety/` evaluates policy and confirmation rules.
- `tools/` perform the actual side effects or data retrieval.
- `memory/` stores and retrieves local data under controlled interfaces.

This separation is intentional. Policy logic should not be embedded directly into tools, and tools should not bypass the router.

## Core Protection Mechanisms

### 1. Schema Validation

All model or user-generated action payloads must pass through `router/schema.py` and `router/dispatch_core.py` before tool execution.

This prevents:

- malformed action payloads,
- unknown action names,
- missing required arguments,
- unexpected arguments not declared by the tool contract.

### 2. Safe Mode And Allowlist Policy

Policy decisions are enforced by `safety/policy_engine.py` using `config/policies.yaml`.

Current rule categories:

- `allow_actions`
- `deny_actions`
- `require_confirmation`

If an action is denied, it is rejected before execution.

If an action requires confirmation, execution stops until the operator explicitly confirms it.

### 3. Confirmation Gates

Write-like or higher-risk actions must not execute silently.

Examples of confirmation-gated behavior include:

- typing text into the system,
- opening applications,
- Android control actions,
- browser workflows that may cause navigation or side effects,
- future PC and mobile control adapters.

This gate is the main protection against accidental local machine actions.

### 4. Audit Logging

Every dispatched action is written to the local audit trail.

Default path:

- `temp/action_audit.jsonl`

Audit records are intended to preserve:

- timestamp,
- normalized request payload,
- result status,
- observation or rejection output,
- policy reason.

This supports:

- debugging,
- operator review,
- policy replay,
- regression checks,
- post-incident analysis.

### 5. Dry-Run Replay

Historical audit records can be replayed through `scripts/replay_audit.py` without re-executing side effects.

This is used to answer:

- would current policy still allow this action,
- would the router still parse and validate this request,
- what changed between earlier and current security logic.

### 6. Trace Sanitization

Sentinel tracing in `debug_utils.py` masks known sensitive values before logging.

Current masking targets include:

- passwords,
- secrets,
- API keys,
- auth tokens,
- credentials,
- clipboard-like sensitive names,
- token-shaped values such as bearer strings and `sk-...` patterns.

This reduces the chance of leaking secrets into debug traces.

## Operator Expectations

The operator is expected to:

1. Run the project from the repository root.
2. Use the project `.venv` instead of a global Python installation.
3. Review policy settings in `config/policies.yaml` before enabling new actions.
4. Keep model downloads, adapters, and system-level binaries aligned with the documented phase goals.
5. Treat future PC, browser, and Android control features as privileged capabilities.

## High-Risk Areas

The following paths require extra caution during code review and testing:

- `router/`
- `safety/`
- `tools/android/`
- `tools/desktop/`
- `tools/web/browser.py`
- `tools/perception/`
- `runtime/`
- `scripts/replay_audit.py`

Any change that alters dispatch behavior, confirmation rules, or tool side effects should include tests for:

- allowed execution,
- denied execution,
- confirmation-required execution,
- dry-run behavior where applicable.

## File System Safety

AI Lan should keep temporary and generated artifacts under:

- `temp/`
- `models/`
- `runs/`

Do not introduce silent writes to arbitrary user locations.

When new file-writing tools are added, they should:

- validate input paths,
- avoid destructive overwrite by default,
- preserve auditability,
- require confirmation for risky write operations.

## Network And External Resources

AI Lan may use external resources only through documented and approved stacks.

Current approved-source guidance lives in:

- `docs/OPEN_SOURCE_REFERENCE.md`
- `docs/RESOURCE_INVENTORY.md`

Before adding new internet-dependent tools, review:

- license,
- maintenance status,
- install footprint,
- safety model,
- ability to keep the dependency behind a local facade.

## Safe Evolution Policy

As Phase 4.2, 4.3, 4.5, and 5.x progress, new capabilities should be added in this order:

1. schema and validation,
2. policy definition,
3. safe stub or read-only implementation,
4. registration in the router,
5. focused tests,
6. documentation updates,
7. only then broader runtime use.

This prevents unsafe capability jumps.

## Incident Response Guidance

If AI Lan behaves unexpectedly:

1. Stop issuing confirmation for write-like actions.
2. Inspect `temp/action_audit.jsonl`.
3. Re-run audit replay with `scripts/replay_audit.py`.
4. Review recent changes in `router/`, `safety/`, and adapter modules.
5. Tighten `config/policies.yaml` before re-enabling the workflow.

## Security Scope Limit

This policy covers local application-level safeguards in the AI Lan repository.

It is not a replacement for:

- operating system security,
- antivirus or endpoint protection,
- credential vaulting,
- disk encryption,
- browser sandboxing,
- network firewall policy.

Those controls remain the responsibility of the machine owner and operating environment.
