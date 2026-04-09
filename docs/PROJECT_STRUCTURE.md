# AI Lan Project Structure

This document defines the target layered architecture for AI Lan and the migration-friendly scaffold added on 2026-04-05.

## Directory Blueprint

```text
ai-lan/
├── core/
│   ├── model/
│   │   ├── transformer.py
│   │   ├── tokenizer.py
│   │   └── config.py
│   ├── inference/
│   │   ├── generate.py
│   │   ├── sampler.py
│   │   └── stopping.py
│   └── quantization/
│       └── dynamic_int8.py
├── agents/
│   ├── react/
│   │   ├── agent.py
│   │   ├── parser.py
│   │   ├── prompt.py
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
│   └── runs/
├── config/
│   ├── settings.yaml
│   ├── tools.yaml
│   └── policies.yaml
├── scripts/
│   ├── train.py
│   ├── evaluate.py
│   └── benchmark.py
├── api/
│   ├── server.py
│   └── routes/
├── main.py
└── README.md
```

## Key Design Principles

1. Strict separation
- agents = thinking
- tools = acting
- memory = remembering
- safety = controlling

2. Tool abstraction layer
- Every tool should follow one common contract (`name`, input schema, `run`).
- This keeps additions safe and predictable.

3. ReAct loop flow
- User input
- Agent thought
- Router selects action
- Safety policy check
- Tool execution
- Observation collection
- Memory update
- Next thought

4. Memory layers
- short-term: current conversation context
- long-term: vector retrieval for prior knowledge
- episodic: historical action/outcome traces
- summaries: compressed durable context

5. Safety-first operation
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
- main.py

## Migration Note

The new structure is scaffolded without deleting the current implementation modules. Existing production paths under actions/, tools/, training/, and scripts/ continue to work while migration proceeds incrementally.
Use [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) as the upstream shortlist for any new `agents/`, `tools/`, `memory/`, or `learning/` integration, and keep the selected dependency behind the repository's own facades.

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
