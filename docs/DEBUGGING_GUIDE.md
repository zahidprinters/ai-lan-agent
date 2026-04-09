# Debugging & Observability Guide 🛡️

This guide explains how to use the **Sentinel Observability System** in AI Lan to debug models, trace variables, and profile performance.

---

## 1. The Sentinel System

Sentinel is a unified observability layer that provides three levels of data capture, controlled by environment variables.

### Environment Variables

| Variable | Values | Description |
| :--- | :--- | :--- |
| `AI_LAN_DEBUG` | `0` (off), `1` (on) | Logs function entry, exit, arguments, and return values. |
| `AI_LAN_TRACE` | `0` (off), `1` (on) | **Automatic Variable Tracking.** Captures every local variable change line-by-line. |
| `AI_LAN_PROFILE` | `0` (off), `1` (on) | **Performance Profiling.** Logs CPU % and Memory (MB) used by each function. |
| `AI_LAN_DEBUG_LOGFILE` | Path string | (Optional) Redirects all sentinel output to a specific file. |

---

## 2. Using the Dashboard

The PowerShell dashboard (`main.ps1`) provides easy toggles for these modes:

1. Run `./main.ps1`.
2. Press **D** to toggle Basic Debugging.
3. Press **T** to toggle Trace Mode (Warning: High log volume).
4. Press **P** to toggle Profiling.

The current status of each mode is displayed in the **Debug & Observability** section of the dashboard.

---

## 3. Finding "Exact Data" with Trace Mode

Trace Mode is designed to show you exactly what is happening inside your functions without needing to add `print()` statements.

### Example Output

```text
2026-04-02 12:00:00 [DEBUG] [SENTINEL] Enter training.trainer.Trainer.train_step
2026-04-02 12:00:00 [DEBUG] [TRACE] line 145: loss = 2.4561
2026-04-02 12:00:00 [DEBUG] [TRACE] line 146: optimizer = <Adam object at ...>
2026-04-02 12:00:00 [DEBUG] [PROFILE] training.trainer.Trainer.train_step: 45.12ms | Mem: +0.02MB | CPU: 12.5%
2026-04-02 12:00:00 [DEBUG] [SENTINEL] Exit training.trainer.Trainer.train_step
```

### Pro Tip

If your model is diverging (loss becomes `NaN`), enable `AI_LAN_TRACE=1`. The logs will show you the exact iteration and variable value where the `NaN` first appeared.

---

## 4. Testing with Sentinel

Tests in AI Lan enable sentinel debug logging by default, while trace/profile remain opt-in to keep test runtime fast.

- Default in tests: `AI_LAN_DEBUG=1`
- Default in tests: `AI_LAN_TRACE=0`
- Default in tests: `AI_LAN_PROFILE=0`

If a test fails and you need deep diagnostics, rerun with explicit trace/profile toggles:

```powershell
$env:AI_LAN_TRACE="1"
$env:AI_LAN_PROFILE="1"
python -m pytest tests\test_file.py -v
```

---

## 5. Implementation for Developers

To add observability to a new function, simply import `sentinel` and use it as a decorator:

```python
from debug_utils import sentinel

@sentinel
def my_new_function(x):
    y = x * 2
    return y
```

Sentinel will automatically handle debugging, tracing, and profiling based on the user's environment settings.
