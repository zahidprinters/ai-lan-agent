# Sentinel Observability System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the project's debugging and profiling capabilities into a high-fidelity "Sentinel" system that automatically tracks every variable change and performance metric.

**Architecture:** A unified `@sentinel` decorator in `debug_utils.py` that uses `sys.settrace` for line-by-line variable tracking and `psutil` for CPU/Memory profiling. All `@debug_log` decorators in the project will be replaced with `@sentinel`.

**Tech Stack:** Python 3.11+, PyTorch, `psutil`, `pytest`.

---

### Task 1: Refactor `debug_utils.py` with the Sentinel Core

**Files:**
- Modify: `debug_utils.py`
- Test: `tests/test_sentinel_core.py` (New)

- [ ] **Step 1: Write failing test for the Sentinel core**

```python
import os
import sys
from pathlib import Path
from debug_utils import sentinel

def test_sentinel_variable_trace(capsys):
    os.environ["AI_LAN_TRACE"] = "1"
    os.environ["AI_LAN_DEBUG"] = "1"
    
    @sentinel
    def sample_func(a):
        b = a + 1
        return b
        
    sample_func(5)
    captured = capsys.readouterr()
    # Check if variable 'b' assignment was captured
    assert "b = 6" in captured.out or "[TRACE] b = 6" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sentinel_core.py -v`
Expected: FAIL (AttributeError: module 'debug_utils' has no attribute 'sentinel')

- [ ] **Step 3: Implement the Sentinel core in `debug_utils.py`**

```python
import functools
import logging
import os
import inspect
import time
import sys
import psutil

_DEBUG_ENV = os.getenv("AI_LAN_DEBUG", "0") == "1"
_TRACE_ENV = os.getenv("AI_LAN_TRACE", "0") == "1"
_PROFILE_ENV = os.getenv("AI_LAN_PROFILE", "0") == "1"
_LOGFILE = os.getenv("AI_LAN_DEBUG_LOGFILE")

def _setup_logger():
    logger = logging.getLogger("sentinel")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        if _LOGFILE:
            fh = logging.FileHandler(_LOGFILE, mode="a", encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        else:
            sh = logging.StreamHandler()
            sh.setFormatter(formatter)
            logger.addHandler(sh)
    return logger

def sentinel_trace_func(frame, event, arg):
    if event == 'line':
        code = frame.f_code
        line_no = frame.f_lineno
        vars = frame.f_locals
        # Log local variables at this line
        logger = _setup_logger()
        for name, value in vars.items():
            try:
                val_repr = repr(value)
                if len(val_repr) > 100: val_repr = val_repr[:97] + "..."
                logger.debug(f"[TRACE] line {line_no}: {name} = {val_repr}")
            except: pass
    return sentinel_trace_func

def sentinel(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = _setup_logger()
        if _DEBUG_ENV:
            logger.debug(f"[SENTINEL] Enter {func.__qualname__}")
        
        # Profiling Start
        start_time = time.perf_counter()
        process = psutil.Process(os.getpid())
        mem_start = process.memory_info().rss / (1024 * 1024)
        cpu_start = process.cpu_percent()

        if _TRACE_ENV:
            sys.settrace(sentinel_trace_func)
            
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            if _TRACE_ENV:
                sys.settrace(None)
            
            # Profiling End
            duration = (time.perf_counter() - start_time) * 1000
            mem_end = process.memory_info().rss / (1024 * 1024)
            cpu_end = process.cpu_percent()
            
            if _PROFILE_ENV:
                logger.debug(f"[PROFILE] {func.__qualname__}: {duration:.2f}ms | Mem: {mem_end - mem_start:+.2f}MB | CPU: {cpu_end:.1f}%")
            if _DEBUG_ENV:
                logger.debug(f"[SENTINEL] Exit {func.__qualname__}")

    return wrapper

# For backward compatibility during migration
debug_log = sentinel
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sentinel_core.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add debug_utils.py tests/test_sentinel_core.py
git commit -m "feat: implement sentinel observability core"
```

---

### Task 2: Update Configuration and Dashboard

**Files:**
- Modify: `training/config.py`
- Modify: `main.ps1`

- [ ] **Step 1: Add new sentinel flags to `ProjectConfig`**

```python
@dataclass
class ProjectConfig:
    # ... existing fields ...
    debug_trace: bool = False
    debug_profile: bool = False
```

- [ ] **Step 2: Update `load_config` to read these flags**

```python
def load_config() -> ProjectConfig:
    # ...
    return ProjectConfig(
        # ...
        debug_trace=os.getenv("AI_LAN_TRACE", "0") == "1",
        debug_profile=os.getenv("AI_LAN_PROFILE", "0") == "1",
    )
```

- [ ] **Step 3: Update `main.ps1` to include Debug/Trace/Profile options**

- [ ] **Step 4: Commit**

```bash
git add training/config.py main.ps1
git commit -m "feat: add sentinel config and dashboard toggles"
```

---

### Task 3: Global Codebase Refactor (Migration)

**Files:**
- Modify: ALL files using `@debug_log`

- [ ] **Step 1: Use Generalist sub-agent to replace `@debug_log` with `@sentinel`**
- [ ] **Step 2: Use Generalist sub-agent to replace `from debug_utils import debug_log` with `from debug_utils import sentinel`**
- [ ] **Step 3: Commit**

---

### Task 4: Centralized Test Observability

**Files:**
- Create: `tests/conftest.py` (if not exists) or Modify

- [ ] **Step 1: Add global sentinel fixture**

```python
import pytest
import os

@pytest.fixture(autouse=True)
def enable_sentinel():
    os.environ["AI_LAN_DEBUG"] = "1"
    os.environ["AI_LAN_TRACE"] = "1"
    os.environ["AI_LAN_PROFILE"] = "1"
    yield
```

- [ ] **Step 2: Commit**

---

### Task 5: Documentation Overhaul

**Files:**
- Create: `docs/DEBUGGING_GUIDE.md`
- Modify: `docs/ARCHITECTURE.md`, `docs/API_REFERENCE.md`, `README.md`

- [ ] **Step 1: Write `docs/DEBUGGING_GUIDE.md`**
- [ ] **Step 2: Update existing docs**
- [ ] **Step 3: Commit**
