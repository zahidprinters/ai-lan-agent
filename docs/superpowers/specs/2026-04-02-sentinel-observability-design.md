# Design Spec: Sentinel Observability System 🛡️

**Date:** 2026-04-02
**Topic:** Comprehensive Debugging, Variable Tracing, and Performance Profiling

---

## 1. Executive Summary
AI Lan requires "exact data" for debugging complex LLM behaviors. This design replaces the existing basic logging with a **Sentinel** system that provides automatic line-by-line variable tracing, CPU/Memory profiling, and centralized test observability.

---

## 2. Technical Architecture

### 2.1 The Sentinel Core (`debug_utils.py`)
A unified decorator `@sentinel` (replacing `@debug_log`) will manage three independent observability layers:

1.  **Basic Layer (Level 1 - `AI_LAN_DEBUG=1`):**
    *   Logs function entry/exit, arguments (repr), and return values.
    *   Captures timestamps and function call depth.

2.  **Trace Layer (Level 2 - `AI_LAN_TRACE=1`):**
    *   Uses `sys.settrace` to monitor local variable assignments.
    *   Logs whenever a variable (e.g., `loss`, `hidden_state`, `tokens`) changes its value.
    *   **Automatic Data Capture:** No manual `print()` calls needed inside functions.

3.  **Profile Layer (Level 3 - `AI_LAN_PROFILE=1`):**
    *   Uses `psutil` and `time.perf_counter`.
    *   Captures `CPU Delta (%)`, `Memory Delta (MB)`, and `Execution Time (ms)` for every function.

### 2.2 Environment Variable Schema

| Variable | Values | Purpose |
| :--- | :--- | :--- |
| `AI_LAN_DEBUG` | `0` (off), `1` (on) | Toggle basic function entry/exit logging. |
| `AI_LAN_TRACE` | `0` (off), `1` (on) | Toggle line-by-line variable value tracking. |
| `AI_LAN_PROFILE`| `0` (off), `1` (on) | Toggle CPU/Memory profiling per function. |
| `AI_LAN_DEBUG_LOGFILE` | Path string | Target file for all observability data. |

---

## 3. Component Updates

### 3.1 Codebase Refactor
*   **Mass Replacement:** Every occurrence of `@debug_log` will be replaced with `@sentinel`.
*   **Breadth:** All functions in `training/`, `tokenizer/`, `models/`, and `tools/` will be decorated.
*   **Centralization:** All imports will point to the new `debug_utils.py`.

### 3.2 Test Mechanism (`tests/conftest.py`)
*   A global `pytest` fixture will be added.
*   It will automatically enable `AI_LAN_DEBUG=1` and `AI_LAN_TRACE=1` during test runs.
*   Test failures will automatically append the specific function trace leading to the failure into the test report.

### 3.3 Dashboard (`main.ps1`)
*   Update `main.ps1` to include a "Debug Mode" toggle that sets these environment variables before running any action.

---

## 4. Documentation Strategy

1.  **`docs/DEBUGGING_GUIDE.md` (New):**
    *   Explains how to interpret "Sentinel Trace" logs.
    *   Provides examples of finding "exact data" to fix model divergence or tokenizer errors.
2.  **`docs/API_REFERENCE.md` & `docs/ARCHITECTURE.md`:**
    *   Update to include the Sentinel layer as a core architectural pillar.
3.  **`README.md`:**
    *   Add a "How to Debug" section for new developers.

---

## 5. Success Criteria
*   [ ] A developer can see the value of a local `loss` variable without adding a `print()` statement.
*   [ ] Every function call reports its memory consumption to identify leaks.
*   [ ] All unit tests pass while generating detailed "sentinel logs" in `temp/`.
