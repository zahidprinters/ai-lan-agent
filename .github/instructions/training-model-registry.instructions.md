---
description: "Use when editing training, checkpoint, evaluation, export, quantization, run-summary, or model-registry code in this repo. Covers checkpoint metadata, summary normalization, registry promotion and rollback, and validation expectations."
name: "Training And Model Registry"
applyTo:
  - "training/**/*.py"
  - "learning/registry/**/*.py"
  - "scripts/train.py"
  - "scripts/evaluate.py"
  - "scripts/export_model.py"
  - "scripts/export_onnx.py"
  - "scripts/quantize_model.py"
  - "scripts/list_runs.py"
  - "scripts/rebuild_run_index.py"
  - "scripts/model_registry.py"
---
# Training And Model Registry Guidelines

- Activate the workspace virtual environment before running Python or training-related commands: `& .venv\Scripts\Activate.ps1`.
- Treat checkpoint metadata as the source of truth for export, evaluation, generation, resume, and registry workflows. Use the shared helpers in [../../training/checkpoints.py](../../training/checkpoints.py) instead of duplicating metadata parsing.
- Preserve compatibility with both legacy flat run summaries and newer nested summary shapes. Normalize summaries before display, sorting, or index rebuilds.
- Quantized checkpoints are inference-only until a dedicated export path exists. Do not route them through generic export flows that expect full-precision weights.
- Keep model and run artifacts in `models/` and `runs/`; keep scratch data and transient caches in `temp/`.
- Do not promote placeholder or invalid artifacts into registry workflows. Preserve promotion, activation, and rollback guards when touching registry code.
- Prefer focused changes that keep existing training and reporting entrypoints compatible across `training/` and `scripts/` wrappers.
- When changing checkpoint, summary, evaluation, export, or registry behavior, add or update focused tests for metadata loading, normalization, and failure handling where feasible.
- Default validation for code changes is `python -m pytest tests -m unit -q --disable-warnings`. Use the broader non-integration suite before finishing larger training or registry changes: `python -m pytest tests -q --disable-warnings --ignore=tests/integration`.
- Use [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md), [../../docs/CONFIGURATION.md](../../docs/CONFIGURATION.md), and [../../docs/OPEN_SOURCE_REFERENCE.md](../../docs/OPEN_SOURCE_REFERENCE.md) for repo-level constraints, and update docs when behavior or workflows change.

## Metadata And Summary Checklist

- Checkpoint load path:
  - config reconstruction remains backward compatible.
  - vocab inference still works for tokenizer metadata and model-state fallback.
- Summary handling:
  - normalized fields remain stable for sorting/display/index rebuild.
  - both legacy flat keys and nested blocks (`metrics`, `hyperparameters`, `data`, `paths`) are handled.
- Registry flow:
  - registration rejects invalid candidates.
  - activation and rollback continue to produce deterministic payloads.

## Safe Workflow Order

1. Modify checkpoint or summary logic with minimal surface area.
2. Add or update focused tests for compatibility and failure mode.
3. Re-run targeted tests, then unit suite.
4. Run non-integration suite for broader changes.
5. Sync docs if behavior, commands, or constraints changed.

## Key Files To Reference

- [../../training/checkpoints.py](../../training/checkpoints.py)
- [../../training/model_registry.py](../../training/model_registry.py)
- [../../scripts/model_registry.py](../../scripts/model_registry.py)
- [../../scripts/rebuild_run_index.py](../../scripts/rebuild_run_index.py)
- [../../docs/AI_CONTEXT.md](../../docs/AI_CONTEXT.md)
- [../../docs/CONFIGURATION.md](../../docs/CONFIGURATION.md)