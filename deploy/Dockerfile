# AI Lan - Production Inference Dockerfile
# Base lean Linux image
FROM python:3.10-slim

# Set non-root user
RUN groupadd -r ailan && useradd -r -g ailan ailan

# Set working directory
WORKDIR /app

# Copy dependency manifests
COPY requirements.txt .

# Install dependencies (CPU-only for production)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir onnxruntime numpy

# Copy core modules and scripts
COPY training/ ./training/
COPY tokenizer/ ./tokenizer/
COPY scripts/infer_simple.py ./scripts/
COPY project_temp.py debug_utils.py ./

# Create necessary directories
RUN mkdir -p models/ data/ runs/ temp/ && \
    chown -r ailan:ailan /app

# Set environment variables
ENV AI_LAN_MODEL_PATH=/app/models/char_model_best.pt
ENV AI_LAN_TOKENIZER_PATH=/app/models/tokenizer.json
ENV PYTHONUNBUFFERED=1

# Expose inference port (if running a future FastAPI wrapper)
EXPOSE 8080

# Switch to non-root user
USER ailan

# Entry point: Run standalone inference on start (or keep alive for worker)
CMD ["python", "scripts/infer_simple.py", "--model", "/app/models/char_model_best.pt"]
