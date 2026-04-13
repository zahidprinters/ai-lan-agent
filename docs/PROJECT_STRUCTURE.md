# AI Lan Project Structure

This document defines the target layered architecture for AI Lan and the migration-friendly scaffold added on 2026-04-05.

## Directory Blueprint

```text
ai-lan/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   ├── workflows/
│   │   └── ci.yml
│   ├── agents/
│   ├── instructions/
│   ├── prompts/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── SECURITY.md
│   └── copilot-instructions.md
├── archive/
│   ├── code/
│   ├── docs/
│   ├── assets/
│   ├── tools/
│   ├── tmp_snapshots/
│   └── ARCHIVE_LOG.md
├── core/
│   ├── model/
│   │   ├── transformer.py
│   │   ├── tokenizer.py
│   │   └── config.py
│   ├── inference/
│   │   ├── context_manager.py
│   │   ├── engine.py
│   │   ├── generate.py
│   │   ├── kv_cache_manager.py
│   │   ├── local_reasoning.py
│   │   ├── model_router.py
│   │   ├── residency.py
│   │   ├── sampler.py
│   │   └── stopping.py
│   ├── quantization/
│   │   └── dynamic_int8.py
│   └── utils/
│       ├── bootstrap.py
│       └── debug.py
├── agents/
│   ├── react/
│   │   ├── agent.py
│   │   ├── parser.py
│   │   ├── planner.py
│   │   ├── prompt.py
│   │   ├── reflection.py
│   │   ├── tool_risk.py
│   │   └── state.py
│   ├── planner/
│   │   ├── task_planner.py
│   │   └── goal_manager.py
│   └── executor/
│       ├── action_executor.py
│       └── observation.py
├── tools/
│   ├── base/
│   │   ├── tool.py
│   │   └── registry.py
│   ├── web/
│   │   ├── search.py
│   │   ├── fetch.py
│   │   └── clean.py
│   ├── system/
│   │   ├── shell.py
│   │   ├── clipboard.py
│   │   └── files.py
│   ├── desktop/
│   │   ├── mouse.py
│   │   ├── keyboard.py
│   │   └── screen.py
│   ├── android/
│   │   ├── adb.py
│   │   ├── input.py
│   │   └── screen.py
│   └── perception/
│       ├── ocr.py
│       └── vision.py
├── memory/
│   ├── short_term/
│   │   └── buffer.py
│   ├── long_term/
│   │   ├── vector_store.py
│   │   ├── embeddings.py
│   │   └── retrieval.py
│   ├── episodic/
│   │   └── actions_log.py
│   └── summaries/
│       └── summarizer.py
├── safety/
│   ├── policy_engine.py
│   ├── validator.py
│   ├── sandbox.py
│   └── confirmation.py
├── router/
│   ├── router.py
│   └── schema.py
├── learning/
│   ├── dataset/
│   │   ├── builder.py
│   │   └── filter.py
│   ├── reward/
│   │   └── reward_model.py
│   ├── training/
│   │   ├── finetune.py
│   │   └── eval.py
│   └── registry/
│       └── model_registry.py
├── runtime/
│   ├── session.py
│   ├── context.py
│   └── scheduler.py
├── logs/
│   ├── actions.log
│   ├── errors.log
│   ├── agent_reasoning.jsonl
│   ├── runtime_errors.jsonl
│   ├── tool_events.jsonl
│   └── runs/
├── models/
│   ├── char_model.pt
│   ├── char_model_best.pt
│   └── gguf/
├── config/
│   ├── settings.yaml
│   ├── tools.yaml
│   └── policies.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── USER_GUIDE.md
│   ├── CONFIGURATION.md
│   ├── API_REFERENCE.md
│   ├── TESTING_GUIDELINES.md
│   └── plans/
│       ├── PHASE_X_MACHINE_PLAN.md
│       ├── ULTIMATE_JARVIS_MASTER_PLAN.md
│       └── FINAL_GOAL_IMPLEMENTATION_PLAN_2026-04-11.md
├── requirements/
│   ├── base.txt
│   └── dev.txt
├── scripts/
│   ├── train.py
│   ├── evaluate.py
│   ├── benchmark.py
│   └── ops/
│       ├── audit_resources.ps1
│       ├── hardware_profile.ps1
│       └── regenerate_resource_inventory.py
├── api/
│   ├── server.py
│   └── routes/
├── _bootstrap.py
├── debug_utils.py
└── README.md
```

## Key Design Principles

1. Strict separation

- agents = thinking
- tools = acting
- memory = remembering
- safety = controlling

1. Tool abstraction layer

- Every tool should follow one common contract (`name`, input schema, `run`).
- This keeps additions safe and predictable.

1. ReAct loop flow

- User input
- Agent thought
- Router selects action
- Safety policy check
- Tool execution
- Observation collection
- Memory update
- Next thought

1. Memory layers

- short-term: current conversation context
- long-term: vector retrieval for prior knowledge
- episodic: historical action/outcome traces
- summaries: compressed durable context

1. Safety-first operation

- deny dangerous shell actions
- require confirmation for file delete, system control, and external side effects
- log every action request and result

## Minimal Working Version

Start and harden this path first:

- agents/react/
- tools/web/search.py
- tools/system/shell.py
- memory/short_term/buffer.py
- router/router.py
- safety/policy_engine.py
- scripts/launch.py

## Migration Note

The new structure is scaffolded without deleting the current implementation modules. Existing production paths under actions/, tools/, training/, and scripts/ continue to work while migration proceeds incrementally.
Use [OPEN_SOURCE_REFERENCE.md](OPEN_SOURCE_REFERENCE.md) as the upstream shortlist for any new `agents/`, `tools/`, `memory/`, or `learning/` integration, and keep the selected dependency behind the repository's own facades.
Compatibility wrappers at repository root (`_bootstrap.py`, `debug_utils.py`) are intentionally retained so legacy imports continue to work while canonical utility implementations live in `core/utils/`.

## Archive Policy

`archive/` is the reversible holding area for anything old, unused, duplicate, extra, or no longer attached to the active project path.

- `archive/code/`: retired modules, old experiments, deprecated compatibility code, unused scripts.
- `archive/docs/`: superseded plans, duplicate writeups, old specs, obsolete guides.
- `archive/assets/`: stale model/data downloads, debug exports, screenshots, binary leftovers, packaged extras.
- `archive/tools/`: retired helper tools, old facades, unused maintenance utilities.
- `archive/tmp_snapshots/`: snapshots from `temp/`, old debug captures, and reversible cleanup bundles.
- `archive/ARCHIVE_LOG.md`: required ledger for every archive move and restore.

Archive-first rule:

- Do not permanently delete cleanup candidates first.
- Move them into `archive/` and log the move.
- Only consider hard deletion after the archive copy is stable and the project no longer depends on the item.

## Embodied AI Package Split

The next extraction target for the CPU-first embodied runtime is a dedicated `perception/` package that keeps vision and audio isolated from action routing.

```text
perception/
├── vision/
│   ├── screen_capture.py
│   ├── camera.py
│   ├── ocr.py
│   └── object_detection.py
└── audio/
    ├── speech_to_text.py
    ├── text_to_speech.py
    └── mic.py
```

Keep `tools/perception/` as the migration-safe facade until the new embodied package is stable and covered by tests.
