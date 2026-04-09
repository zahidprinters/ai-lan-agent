# Global Codebase Refactor: @debug_log to @sentinel Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all occurrences of `@debug_log` decorator and its associated imports with `@sentinel` across the entire project.

**Architecture:** Systematic replacement of imports and decorators in Python files. Maintaining backward compatibility only in `debug_utils.py`.

**Tech Stack:** Python, `grep`, `replace`.

---

### Task 1: Update `training/*.py`

**Files:**
- `training/__init__.py`
- `training/train_char_model.py`
- `training/trainer.py`
- `training/metrics.py`
- `training/inference.py`
- `training/generate.py`
- `training/factory.py`
- `training/dataset.py`
- `training/corpus.py`
- `training/config.py`
- `training/checkpoints.py`

- [ ] **Step 1: Replace imports and decorators in `training/*.py`**

```python
# Replace
from debug_utils import debug_log
# with
from debug_utils import sentinel

# Replace
@debug_log
# with
@sentinel
```

- [ ] **Step 2: Commit**

```bash
git add training/*.py
git commit -m "refactor: migrate @debug_log to @sentinel in training module"
```

### Task 2: Update `training/models/*.py`

**Files:**
- `training/models/__init__.py`
- `training/models/transformer.py`
- `training/models/recurrent.py`
- `training/models/char_mlp.py`
- `training/models/bigram.py`

- [ ] **Step 1: Replace imports and decorators in `training/models/*.py`**

```python
# Replace
from debug_utils import debug_log
# with
from debug_utils import sentinel

# Replace
@debug_log
# with
@sentinel
```

- [ ] **Step 2: Commit**

```bash
git add training/models/*.py
git commit -m "refactor: migrate @debug_log to @sentinel in models module"
```

### Task 3: Update `tokenizer/*.py`

**Files:**
- `tokenizer/__init__.py`
- `tokenizer/factory.py`
- `tokenizer/char_tokenizer.py`
- `tokenizer/bpe_tokenizer.py`

- [ ] **Step 1: Replace imports and decorators in `tokenizer/*.py`**

```python
# Replace
from debug_utils import debug_log
# with
from debug_utils import sentinel

# Replace
@debug_log
# with
@sentinel
```

- [ ] **Step 2: Commit**

```bash
git add tokenizer/*.py
git commit -m "refactor: migrate @debug_log to @sentinel in tokenizer module"
```

### Task 4: Update `tools/*.py`

**Files:**
- `tools/web_search.py`
- `tools/pc_control.py`

- [ ] **Step 1: Replace imports and decorators in `tools/*.py`**

```python
# Replace
from debug_utils import debug_log
# with
from debug_utils import sentinel

# Replace
@debug_log
# with
@sentinel
```

- [ ] **Step 2: Commit**

```bash
git add tools/*.py
git commit -m "refactor: migrate @debug_log to @sentinel in tools module"
```

### Task 5: Final Verification and Cleanup

- [ ] **Step 1: Verify all occurrences are replaced except in `debug_utils.py`**

Run: `grep -r "debug_log" .`
Expected: Only matches in `debug_utils.py` for backward compatibility.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_sentinel_core.py`
Expected: All tests pass.

- [ ] **Step 3: Final Commit**

```bash
git commit -m "refactor: complete @debug_log to @sentinel migration"
```
