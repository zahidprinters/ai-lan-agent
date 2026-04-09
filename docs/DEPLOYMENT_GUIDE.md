# AI Lan Cloud Deployment Guide 🚀

This document outlines how to deploy AI Lan for high-scale inference using Docker and cloud providers (AWS, GCP, Azure).

---

## 🐳 Containerization (Docker)

AI Lan is optimized for containerized environments. Use the provided `deploy/Dockerfile` to build a lean, production-ready image.

### 1. Build the Image

```bash
docker build -t ai-lan-inference -f deploy/Dockerfile .
```

### 2. Run Locally (Testing)

```bash
docker run -p 8080:8080 ai-lan-inference
```

---

## ☁️ Cloud Deployment Workflows

### Scenario A: Google Cloud Run (Serverless)

Best for cost-efficiency. Scale to zero when not in use.

1. Push your image to **Google Container Registry (GCR)**.
2. Deploy as a Cloud Run service using the ONNX-optimized build.
3. Use the `/infer` endpoint for rapid prompt responses.

### Scenario B: AWS EC2 (Continuous Performance)

Best for dedicated, high-availability researchers.

1. Provision a `t3.medium` instance (CPU-only is sufficient).
2. Install Docker and run the image.
3. Map a persistent volume to `/app/models` to store and update refined brains.

---

## ⚡ Deployment Optimizations

### ONNX Runtime

For production, export your model to **ONNX** using `python scripts/export_onnx.py --model models/char_model_best.pt`. The export command now checks for both `onnx` and `onnxruntime` and exits with a clear error if either package is missing.

The project dependency baseline pins ONNX Runtime to `onnxruntime==1.20.1` in `requirements.txt`, and this should remain aligned with the active virtual environment for stable CPU inference behavior.

The standalone inference script (`scripts/infer_simple.py`) reads the ONNX metadata sidecar produced during export so it can recover the correct block size and tokenizer context on CPU.

### Quantization (Save 75% RAM)

If deploying on memory-constrained edge devices (Raspberry Pi, low-tier VPS), use the **Quantized Model** produced by `python scripts/quantize_model.py --model models/char_model_best.pt`.

Quantized checkpoints currently target the PyTorch inference path and are treated as inference-only artifacts. The generic export helper rejects them until a dedicated export route is added.

---

## 📝 Footer Note

Created by Nadeem Abbas | 🌌 AI Lan Project - Level 4 Autonomy Ready
