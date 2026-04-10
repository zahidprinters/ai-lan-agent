# Open Source Reference Index

Curated upstream shortlist for AI Lan Phase 3 to Phase 5 work.

Selection rules:
- Prefer official repos and official docs first.
- Check license, maintenance activity, and install footprint before adoption.
- Keep every external dependency behind local facades in `core/`, `agents/`, `tools/`, `memory/`, or `learning/`.
- Add tests before wiring any new project into the live path.
- Start with one project per capability instead of stacking overlapping libraries.

Adoption order:
- Phase 4: one agent framework, one browser stack, one search stack, one OCR stack, one Android stack.
- Phase 4.5: one vision stack, one speech-to-text stack, one text-to-speech stack, one CPU LLM runtime.
- Phase 5: one memory backend, one finetuning stack, one dataset pipeline, one orchestration layer, one home automation target.

## Training and Fine-Tuning

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| nanoGPT | https://github.com/karpathy/nanoGPT | Small, readable GPT training reference for the current architecture level. |
| lit-gpt | https://github.com/Lightning-AI/litgpt | Cleaner production-style GPT training, finetuning, and quantization patterns. |
| tinygrad | https://github.com/tinygrad/tinygrad | Extreme low-level control if you want the thinnest possible stack. |
| PEFT | https://github.com/huggingface/peft | Lightweight adapter-based finetuning for Phase 5 personalization. |
| LoRA | https://github.com/microsoft/LoRA | Canonical low-rank adapter reference. |
| QLoRA | https://github.com/artidoro/qlora | Quantized finetuning recipe for small hardware budgets. |
| TRL | https://github.com/huggingface/trl | Post-training, reward, and preference-optimization workflows. |
| datasets | https://github.com/huggingface/datasets | Dataset loading, filtering, streaming, and preprocessing. |
| DeepSpeed | https://github.com/deepspeedai/DeepSpeed | Scale-oriented training and inference optimization when local limits are hit. |

Best fit for AI Lan:
- Use `nanoGPT` or `lit-gpt` as the main training reference.
- Use `PEFT`, `LoRA`, `QLoRA`, and `TRL` for Phase 5 self-improvement.
- Use `datasets` for corpus and learning-pipeline construction.

## Agent Frameworks and Coding Apps

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| LangChain | https://github.com/langchain-ai/langchain | Broad tool, memory, retrieval, and pipeline ecosystem. |
| LangGraph | https://github.com/langchain-ai/langgraph | State-machine style agent orchestration and durable flows. |
| Semantic Kernel | https://github.com/microsoft/semantic-kernel | Plugin-centric orchestration for tool use and planning. |
| AutoGen | https://github.com/microsoft/autogen | Multi-agent coordination reference and conversation patterns. |
| Microsoft Agent Framework | https://github.com/microsoft/agent-framework | Modern Microsoft agent runtime to study for structured workflows. |
| CrewAI | https://github.com/crewAIInc/crewAI | Multi-agent crews and role-based orchestration patterns. |
| OpenAI Agents SDK | https://github.com/openai/openai-agents-python | Lightweight agent/app patterns and handoffs. |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | Full coding-agent app for software tasks and tool use. |
| Aider | https://github.com/Aider-AI/aider | Repo-aware terminal coding assistant and edit loop. |
| Continue | https://github.com/continuedev/continue | IDE-oriented coding assistant and workflow reference. |
| Open Interpreter | https://github.com/openinterpreter/open-interpreter | Natural-language computer-use and code-execution reference. |
| OpenCodeInterpreter | https://github.com/OpenCodeInterpreter/OpenCodeInterpreter | Coding agent with execution and refinement loop. |
| OpenAgents | https://github.com/xlang-ai/OpenAgents | Agent platform patterns for plugins, web, and data tools. |
| OpenCUA | https://github.com/xlang-ai/OpenCUA | Computer-use agent framework and benchmark reference. |
| Letta | https://github.com/letta-ai/letta | Stateful agent runtime and long-term memory patterns (MemGPT successor). |

Best fit for AI Lan:
- Start with `Semantic Kernel`, `LangGraph`, or `LangChain` and choose one.
- Study `OpenHands`, `Aider`, `Continue`, and `Open Interpreter` for app-level agent UX.
- Use `Letta` if you want the strongest long-term state and memory reference.

## Browser, Search, and MCP

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| Playwright | https://github.com/microsoft/playwright | Primary browser automation stack for reliable web control. |
| Playwright MCP | https://github.com/microsoft/playwright-mcp | Agent-friendly browser control through MCP-style tool access. |
| Selenium | https://github.com/SeleniumHQ/selenium | Broad browser automation fallback with mature ecosystem support. |
| browser-use | https://github.com/browser-use/browser-use | LLM-friendly browser workflows and web task execution. |
| browser-use-python | https://github.com/browser-use/browser-use-python | Python-side browser-use integration reference. |
| Tavily Python | https://github.com/tavily-ai/tavily-python | Search/extract/crawl API for live web context. |
| Tavily MCP | https://github.com/tavily-ai/tavily-mcp | MCP wrapper for search-backed tool use. |
| SerpApi Python | https://github.com/serpapi/google-search-results-python | Structured search results when you need provider-backed search. |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | Build your own tool servers and agent-tool bridges. |
| MCP Servers | https://github.com/modelcontextprotocol/servers | Reference implementations for common tool servers. |

Best fit for AI Lan:
- Prefer `Playwright` for browser control.
- Use `browser-use` when you want agent-native web workflows.
- Use `Tavily` for search and `MCP` when you want a clean tool-server boundary.

## Desktop and Android Control

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| PyAutoGUI | https://github.com/asweigart/pyautogui | Cross-platform mouse and keyboard automation fallback. |
| pynput | https://github.com/moses-palmer/pynput | Low-level keyboard and mouse hooks. |
| ADB | https://developer.android.com/tools/adb | Official Android command-line control surface. |
| scrcpy | https://github.com/Genymobile/scrcpy | Low-latency Android display and control bridge. |
| Appium | https://github.com/appium/appium | Cross-platform mobile automation reference. |
| uiautomator2 | https://github.com/openatx/uiautomator2 | Android UI automation layer for deeper device control. |
| Appium MCP | https://github.com/appium/appium-mcp | MCP-style mobile control integration reference. |

Best fit for AI Lan:
- Use `Playwright` first for web tasks before desktop automation.
- Use `PyAutoGUI` or `pynput` only for local fallback control.
- Use `ADB` and `scrcpy` for Phase 4 Android work, then add `Appium` or `uiautomator2` only if needed.

## Perception and Screen Understanding

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| OpenCV | https://github.com/opencv/opencv | Core computer-vision and frame-processing library for screenshots and camera frames. |
| mss | https://github.com/BoboTiG/python-mss | Fast, low-overhead screen capture for desktop screenshots. |
| Tesseract OCR | https://github.com/tesseract-ocr/tesseract | Mature OCR engine and training reference. |
| EasyOCR | https://github.com/JaidedAI/EasyOCR | Simple OCR API with good Python ergonomics. |
| Segment Anything | https://github.com/facebookresearch/segment-anything | Visual grounding and segmentation reference. |
| Ultralytics | https://github.com/ultralytics/ultralytics | Detection, segmentation, and training workflows. |

Best fit for AI Lan:
- Use `mss` for fast screen capture and `OpenCV` for frame processing.
- Start with `Tesseract` for OCR.
- Add `EasyOCR` if you want a simpler Python path.
- Use `Ultralytics` or `SAM` only when stronger visual grounding is worth the added complexity.

## Speech, Voice, and Local Reasoning

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| Vosk API | https://github.com/alphacep/vosk-api | Offline speech-to-text for low-CPU, real-time listening. |
| whisper.cpp | https://github.com/ggml-org/whisper.cpp | CPU-first Whisper transcription when you want better accuracy than Vosk. |
| PyAudio | https://github.com/CristiFati/pyaudio | Python microphone and audio-stream access built on PortAudio. |
| PortAudio | https://github.com/PortAudio/portaudio | Cross-platform audio I/O backend for capture and playback. |
| Coqui TTS | https://github.com/coqui-ai/TTS | Natural-sounding offline text-to-speech for heavier but higher-quality output. |
| pyttsx3 | https://github.com/nateshmbhat/pyttsx3 | Very light offline TTS fallback for CPU-only environments. |
| llama.cpp | https://github.com/ggml-org/llama.cpp | Local CPU LLM runtime and OpenAI-compatible server for reasoning. |
| llama-cpp-python | https://github.com/abetlen/llama-cpp-python | Python bindings and server wrapper for llama.cpp integration. |

Best fit for AI Lan:
- Use `Vosk` for the minimum viable offline speech recognizer.
- Use `pyttsx3` for the minimum viable offline speaker.
- Use `llama.cpp` or `llama-cpp-python` for local reasoning and tool selection.
- Upgrade to `whisper.cpp` and `Coqui TTS` only when the accuracy or voice quality tradeoff is worth the extra CPU cost.

## Voice Assistant Apps and Skills

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| OpenVoiceOS Core | https://github.com/OpenVoiceOS/ovos-core | Maintained open-source voice assistant platform with a real skills ecosystem. |
| OVOS Skills Store | https://github.com/OpenVoiceOS/OVOS-skills-store | Reference for packaging, browsing, and distributing skills. |

Best fit for AI Lan:
- Study `OpenVoiceOS` if you want a real skills/app architecture around voice commands and device control.
- Use the skills store as a reference for how to package and distribute reusable capabilities.

## Memory and Retrieval

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| Chroma | https://github.com/chroma-core/chroma | Lightweight AI-focused vector retrieval database. |
| Qdrant | https://github.com/qdrant/qdrant | Production-grade vector database with strong ecosystem support. |
| FAISS | https://github.com/facebookresearch/faiss | Low-level vector similarity library. |
| Letta | https://github.com/letta-ai/letta | Stateful memory and agent context management (formerly MemGPT). |

Best fit for AI Lan:
- Use `Chroma` or `Qdrant` as the first durable memory backend.
- Use `FAISS` when you want a lower-level retrieval engine.

## Self-Learning and Orchestration

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| Ray | https://github.com/ray-project/ray | Distributed execution for evaluation and training jobs. |
| Airflow | https://github.com/apache/airflow | Scheduled workflow orchestration for nightly jobs. |

Best fit for AI Lan:
- Use `Ray` or `Airflow` only when the pipeline actually needs distributed or scheduled execution.

## Home and IoT Control

| Project | URL | Best use in AI Lan |
| --- | --- | --- |
| Home Assistant | https://github.com/home-assistant/core | Local-first home automation platform. |
| ESPHome | https://github.com/esphome/esphome | Firmware/configuration platform for ESP devices. |

Best fit for AI Lan:
- Use `Home Assistant` as the Phase 5 smart-home target.
- Use `ESPHome` when you need custom device control surfaces.

## Practical Next Stack

If you want a focused build path instead of many tools at once:

1. Training reference: `nanoGPT` or `lit-gpt`
2. Agent framework: `Semantic Kernel`, `LangGraph`, or `LangChain`
3. Browser automation: `Playwright`
4. Search: `Tavily`
5. OCR: `Tesseract`
6. Android: `ADB` + `scrcpy`
7. Memory: `Chroma` or `Qdrant`
8. Self-learning: `PEFT` + `LoRA` + `QLoRA` + `TRL`
9. Orchestration: `datasets` first, then `Ray` or `Airflow` if needed
10. Embodied CPU stack: `mss` + `OpenCV` + `Tesseract` + `Vosk` + `pyttsx3` + `llama.cpp`
11. Coding-app references: `OpenHands`, `Aider`, `Continue`, and `Open Interpreter`

This keeps the project aligned with the layered architecture while leaving room to grow safely.

## Windows Install Snapshot (Validated)

Current optional Phase 4 stack validated in this workspace:

- Python packages: `playwright==1.58.0`, `tavily-python==0.7.23`, `pytesseract==0.3.13`
- System tools: `Tesseract OCR`, `ADB` (Android Platform-Tools), `scrcpy`

Commands:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
winget install --id Google.PlatformTools -e --accept-package-agreements --accept-source-agreements
winget install --id Genymobile.scrcpy -e --accept-package-agreements --accept-source-agreements
```

If you use Tavily live search, set:

```powershell
$env:TAVILY_API_KEY = "<your_api_key>"
```
