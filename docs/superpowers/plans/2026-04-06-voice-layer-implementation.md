# Phase 4.5: Voice Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an always-listening offline voice interface using Vosk for STT and pyttsx3 for TTS.

**Architecture:**
- **STT (Vosk):** Continuous background listening for "AI Lan" wake word and command transcription.
- **TTS (pyttsx3):** Local system voice output with selectable male/female profiles.
- **Voice Controller:** Orchestrates the audio loop and pipes text to the Neural Action Controller.

**Tech Stack:** Python, `vosk`, `pyttsx3`, `pyaudio`, `Pillow`.

---

### Task 1: Dependencies & Configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `training/config.py`

- [ ] **Step 1: Add voice libraries to `requirements.txt`**
```text
vosk==0.3.45
pyttsx3==2.90
PyAudio==0.2.14
```

- [ ] **Step 2: Add Voice settings to `ProjectConfig` in `training/config.py`**
```python
voice_enabled: bool = False
wake_word: str = "ai lan"
voice_gender: str = "female"  # "male" or "female"
voice_rate: int = 175
```

- [ ] **Step 3: Update `load_config` to read environment variables**
```python
voice_enabled=os.getenv("AI_LAN_VOICE_ENABLED", "0") == "1",
wake_word=os.getenv("AI_LAN_WAKE_WORD", "ai lan").lower(),
voice_gender=os.getenv("AI_LAN_VOICE_GENDER", "female").lower(),
voice_rate=int(os.getenv("AI_LAN_VOICE_RATE", "175")),
```

- [ ] **Step 4: Install dependencies in `.venv`**
Run: `.\.venv\Scripts\python.exe -m pip install vosk pyttsx3 PyAudio`

- [ ] **Step 5: Commit**

---

### Task 2: Text-to-Speech (TTS) Implementation

**Files:**
- Create: `tools/perception/audio/tts.py`
- Test: `tests/test_tts.py`

- [ ] **Step 1: Implement `Speaker` class with `pyttsx3`**
```python
import pyttsx3
from training.config import load_config

class Speaker:
    def __init__(self):
        self.config = load_config()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.config.voice_rate)
        self._set_gender(self.config.voice_gender)

    def _set_gender(self, gender: str):
        voices = self.engine.getProperty('voices')
        # Check if voices exist and handle accordingly
        if not voices:
            return
        # Usually 0 is male, 1 is female on Windows
        if gender == "male":
            self.engine.setProperty('voice', voices[0].id)
        else:
            self.engine.setProperty('voice', voices[min(1, len(voices)-1)].id)

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
```

- [ ] **Step 2: Write basic test for TTS initialization**
- [ ] **Step 3: Commit**

---

### Task 3: Speech-to-Text (STT) Implementation

**Files:**
- Create: `tools/perception/audio/stt.py`
- Test: `tests/test_stt.py`

- [ ] **Step 1: Implement `Listener` class with `Vosk`**
- [ ] **Step 2: Implement Wake Word detection logic**
- [ ] **Step 3: Commit**

---

### Task 4: Voice Chat Controller

**Files:**
- Create: `scripts/voice_chat.py`

- [ ] **Step 1: Implement the main loop in `scripts/voice_chat.py`**
- [ ] **Step 2: Integrate with `ChatSession` for action routing**
- [ ] **Step 3: Commit**

---

### Task 5: Documentation & Map Update

**Files:**
- Modify: `docs/AGENCY_MAP.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1: Add Voice Loop to the Agency Map**
- [ ] **Step 2: Update file structure with `perception/audio/`**
- [ ] **Step 3: Commit**
