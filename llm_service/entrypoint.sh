#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="/app/models/llama-3.2-3b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

echo "LLM startup: checking model at ${MODEL_PATH}"
if [ ! -f "${MODEL_PATH}" ]; then
  echo "Model not found. Downloading from Hugging Face..."
  mkdir -p /app/models
  wget -O "${MODEL_PATH}" "${MODEL_URL}"
else
  echo "Model already present."
fi

exec uvicorn app:app --host 0.0.0.0 --port 8000
