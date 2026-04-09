# AI Lan User Guide 📘

Welcome to **AI Lan**! This guide provides end-users with the information needed to train, test, and use local language models effectively.

---

## 🛠️ Getting Started

Before performing any action, ensure you are in the project's root directory and have your Python environment set up correctly.

### 1. Launching the Dashboard

The dashboard is the central hub for all AI Lan actions. To launch it, run the following command in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File main.ps1
```

Once the dashboard is open, you can simply type the **number** corresponding to the action you wish to perform (e.g., `3` to train).

---

## 🚀 Key Actions & Workflows

### 📍 Action 3: Train Model

- **What it does:** Reads your training data (`data/input.txt`) and trains the selected model.
- **Result:** Saves a `models/char_model_best.pt` file.

### 📍 Action 4: Generate Text

- **What it does:** Uses your trained model to generate new text based on a prompt.
- **Result:** Displays the generated text in your console.

### 📍 Action 11: Dataset Report

- **What it does:** Analyzes the quality of your training data.

---

## 🚀 Advanced Workflows

### 📍 Deploying to High-Performance Environments

For production or edge deployment, use the **ONNX** or **Quantization** pipelines:

1. **Export to ONNX**: `python scripts/export_onnx.py --model models/char_model_best.pt`
2. **Quantize for CPU**: `python scripts/quantize_model.py --model models/char_model_best.pt`
3. **Fast Evaluation**: Use `scripts/evaluate.py` to benchmark performance metrics.

The export path now checks for `onnx` and `onnxruntime` up front, and the ONNX inference path reads the metadata sidecar written during export. Quantized checkpoints are currently intended for the PyTorch inference path, so keep them out of generic export workflows.

### 📍 Cross-Platform Training (Linux/WSL)

AI Lan is fully cross-platform. Use standard environment variables for acceleration:

```bash
export AI_LAN_DEVICE='cuda'  # For NVIDIA GPUs
export AI_LAN_USE_AMP='1'     # For high-speed training
python training/train_char_model.py
```

### 📍 Real-World Workflow: Agentic ReAct

To experiment with "reasoning" workflows, prepare a dataset that includes "Thought/Action/Observation" patterns:

1. **Prepare Data**: Craft `input.txt` with examples like:
   `User: What is AI? Thought: I should search for AI definition. Action: WebSearch("AI definition") Observation: AI is...`
2. **Train Model**: Use a larger `transformer` profile.
3. **Run Inference**: Use `training/inference.py` with `stop_sequences=["Observation:"]`.

### 📍 Real-World Workflow: Narrative Logic

For high-quality storytelling logic, use the pre-curated TinyStories dataset:

1. **Fetch Data**: Run `python scripts/fetch_tinystories.py`.
2. **Train Model**: Set `AI_LAN_DATA_PATH="data/tinystories.txt"` and train for at least 10 epochs.
3. **Quantize**: To shrink your story-brain for mobile deployment, run `python scripts/quantize_model.py`.

### 📍 Real-World Workflow: Continuous Internet Data Feed

To improve model quality using external free resources:

1. Curate trusted text sources (public datasets, docs, articles, transcripts).
2. Normalize and deduplicate corpus (`python scripts/clean_dataset.py`).
3. Merge curated sources into one corpus (`scripts/merge_corpus.ps1`).
4. Run quality report (`python scripts/data_report.py`).
5. Retrain with fixed profile and compare run summaries in `runs/`.

When you review run summaries, the leaderboard tooling now normalizes both legacy flat summaries and newer nested summaries automatically, so you can compare old and new runs side by side.

### 📍 Real-World Workflow: Embodied CPU Mode

If you want the lightest embodied setup for a CPU-only machine, start with:

1. **Eyes:** `mss` for screenshots, `OpenCV` for frame handling, and `Tesseract` for OCR.
2. **Ears:** `Vosk` for offline speech-to-text.
3. **Voice:** `pyttsx3` for offline speech output.
4. **Brain:** `llama.cpp` for local reasoning.

Once that works, upgrade selectively with `whisper.cpp`, `Coqui TTS`, `EasyOCR`, or `Ultralytics` only if the extra cost is justified.

### 📍 Phase 4/5 Expansion Note

If you are extending AI Lan beyond the current user workflows, start from [docs/OPEN_SOURCE_REFERENCE.md](docs/OPEN_SOURCE_REFERENCE.md) and keep to one project per capability.
The shortest safe Phase 4 path is `Playwright` + `Tavily` + `Tesseract` + `ADB`/`scrcpy` behind the router.
The shortest safe Phase 4.5 path is `mss`/`OpenCV` + `Tesseract` + `Vosk` + `pyttsx3` + `llama.cpp`.
The shortest safe Phase 5 path is `Chroma` or `Qdrant` plus `PEFT` + `LoRA` + `QLoRA` + `TRL`.

If you are touching export, evaluation, generation, or training resume code, keep checkpoint metadata as the source of truth first and use the shared loaders that already do this correctly.

---

## 🛠️ Troubleshooting & Optimization

| Issue | Potential Solution |
| :--- | :--- |
| **CUDA Out of Memory (OOM)** | Decrease `AI_LAN_BATCH_SIZE` or `AI_LAN_HIDDEN_SIZE`. |
| **Loss is 'NaN'** | Ensure `AI_LAN_LEARNING_RATE` is not too high (e.g., 1e-4). |
| **Slow Training on CPU** | Enable `AI_LAN_USE_AMP='1'`. |
| **Generation is Repetitive** | Increase `AI_LAN_GENERATE_TEMPERATURE` (1.2+) or set `top_p=0.9`. |
| **FileNotFound in Tests** | Ensure your isolated test environment has established a `runs/` directory. |

---

*Developed by Nadeem Abbas | 🌌 AI Lan Project | [Phase 3.0 Stabilized & Phase 4.0 Ready]*
