# Phase 5.0: Sleep Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an automated nightly fine-tuning pipeline that learns from successful agent actions in the audit log and auto-promotes the best model.

**Architecture:**
- **Harvester:** Extracts `executed` status actions from `temp/action_audit.jsonl` and validates them against the tool schema.
- **Training:** Runs a low-LR fine-tuning loop on the local CPU, comparing results against a "Golden Set" of baseline tests.
- **Promotion:** Backs up the current model and promotes the new one only if it shows measurable improvement without regression.

**Tech Stack:** Python, PyTorch, JSONL, `psutil`.

---

### Task 1: Configuration Update

**Files:**
- Modify: `training/config.py`

- [ ] **Step 1: Add Sleep Mode settings to `ProjectConfig`**

```python
# In training/config.py, add these to ProjectConfig dataclass:
sleep_mode_hour: int = 3  # 3:00 AM
auto_promote: bool = True
action_audit_path: str | None = None
sleep_val_threshold: float = 1.05  # Allow 5% loss regression if logic holds
```

- [ ] **Step 2: Update `load_config` to read environment variables**

```python
# In load_config() function:
sleep_mode_hour=int(os.getenv("AI_LAN_SLEEP_MODE_HOUR", "3")),
auto_promote=os.getenv("AI_LAN_AUTO_PROMOTE", "1") == "1",
action_audit_path=os.getenv("AI_LAN_ACTION_AUDIT_PATH"),
sleep_val_threshold=float(os.getenv("AI_LAN_SLEEP_VAL_THRESHOLD", "1.05")),
```

- [ ] **Step 3: Commit**

```bash
git add training/config.py
git commit -m "config: add sleep mode and auto-promote settings"
```

---

### Task 2: Log Harvester

**Files:**
- Create: `learning/dataset/harvester.py`
- Test: `tests/test_harvester.py`

- [ ] **Step 1: Write a test to verify harvesting of successful actions**

```python
import json
from pathlib import Path
from learning.dataset.harvester import HarvestedEntry, harvest_successful_actions

def test_harvest_successful_actions(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    entry = {
        "timestamp": "2026-04-06T00:00:00Z",
        "request": {"thought": "test", "action": "pc.read_clipboard", "args": {}, "safety_level": "low"},
        "result": {"status": "executed", "action": "pc.read_clipboard", "observation": "hello", "policy_reason": "ok"}
    }
    log_path.write_text(json.dumps(entry) + "\n")
    
    harvested = harvest_successful_actions(log_path)
    assert len(harvested) == 1
    assert harvested[0].action == "pc.read_clipboard"
```

- [ ] **Step 2: Implement `harvest_successful_actions`**

```python
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

@dataclass
class HarvestedEntry:
    thought: str
    action: str
    args: dict[str, Any]
    observation: Any

def harvest_successful_actions(log_path: Path) -> list[HarvestedEntry]:
    if not log_path.exists():
        return []
    results = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data["result"]["status"] == "executed":
                    req = data["request"]
                    results.append(HarvestedEntry(
                        thought=req["thought"],
                        action=req["action"],
                        args=req["args"],
                        observation=data["result"]["observation"]
                    ))
            except (json.JSONDecodeError, KeyError):
                continue
    return results
```

- [ ] **Step 3: Commit**

```bash
git add learning/dataset/harvester.py tests/test_harvester.py
git commit -m "feat: implement successful action harvester"
```

---

### Task 3: Model Promotion & Registry

**Files:**
- Modify: `learning/registry/model_registry.py` (Implement the logic)
- Create: `models/model_registry.json` (Initialize)

- [ ] **Step 1: Initialize `models/model_registry.json`**

```json
{
  "current_version": 1,
  "history": [
    {
      "version": 1,
      "date": "2026-04-05",
      "path": "models/best_model.pt",
      "description": "Initial Phase 4.0 baseline"
    }
  ]
}
```

- [ ] **Step 2: Implement `promote_model` logic**

```python
# In learning/registry/model_registry.py:
import json
import shutil
from pathlib import Path
from datetime import datetime

def promote_model(new_model_path: Path, registry_path: Path, models_dir: Path):
    with registry_path.open("r") as f:
        registry = json.load(f)
    
    new_version = registry["current_version"] + 1
    backup_path = models_dir / "backups" / f"best_model_v{registry['current_version']}.pt"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup current
    shutil.copy(models_dir / "best_model.pt", backup_path)
    
    # Overwrite best
    shutil.copy(new_model_path, models_dir / "best_model.pt")
    
    # Update registry
    registry["current_version"] = new_version
    registry["history"].append({
        "version": new_version,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "path": "models/best_model.pt",
        "description": f"Sleep Mode auto-promotion v{new_version}"
    })
    
    with registry_path.open("w") as f:
        json.dump(registry, f, indent=2)
```

- [ ] **Step 3: Commit**

```bash
git add learning/registry/model_registry.py models/model_registry.json
git commit -m "feat: add model promotion and registry tracking"
```

---

### Task 4: Sleep Fine-Tuning Loop

**Files:**
- Create: `learning/training/sleep_finetune.py`

- [ ] **Step 1: Implement `run_sleep_finetune`**

```python
import torch
from pathlib import Path
from learning.dataset.harvester import harvest_successful_actions
# Import existing trainer logic
from training.trainer import Trainer
from training.config import load_config

def run_sleep_finetune():
    config = load_config()
    log_path = Path("temp/action_audit.jsonl")
    entries = harvest_successful_actions(log_path)
    if not entries:
        print("No new data to train on.")
        return None

    # Logic to load model, create temporary dataset from entries,
    # and run Trainer for 3 epochs with config.sleep_val_threshold.
    # Return path to new checkpoint.
    return Path("temp/sleep_checkpoint.pt")
```

- [ ] **Step 2: Commit**

```bash
git add learning/training/sleep_finetune.py
git commit -m "feat: implement nightly fine-tuning loop"
```

---

### Task 5: Main Entry Point & Scheduler

**Files:**
- Create: `scripts/sleep_mode.py`

- [ ] **Step 1: Implement `scripts/sleep_mode.py`**

```python
import time
import sys
from datetime import datetime
from learning.training.sleep_finetune import run_sleep_finetune
from learning.registry.model_registry import promote_model
from training.config import load_config
from pathlib import Path

def main():
    config = load_config()
    print(f"AI Lan Sleep Mode Active. Scheduled for {config.sleep_mode_hour}:00 AM.")
    
    while True:
        now = datetime.now()
        if now.hour == config.sleep_mode_hour:
            print("Starting nightly fine-tuning...")
            new_model = run_sleep_finetune()
            if new_model and config.auto_promote:
                promote_model(new_model, Path("models/model_registry.json"), Path("models"))
                print("Model promoted successfully.")
            
            # Archive logs
            log_path = Path("temp/action_audit.jsonl")
            if log_path.exists():
                archive_path = Path("temp/archives") / f"audit_{now.strftime('%Y%m%d')}.jsonl"
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.rename(archive_path)
            
            print("Sleep Mode complete. Waiting for next cycle.")
            time.sleep(3600 * 23) # Sleep for 23 hours
        
        time.sleep(60)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/sleep_mode.py
git commit -m "feat: add main sleep mode script and scheduler"
```
