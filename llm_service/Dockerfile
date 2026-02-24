
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para compilar llama-cpp
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instalar llama-cpp-python y fastapi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Creamos directorio para el modelo si no existe
RUN mkdir -p /app/models

# Script de descarga del modelo GGUF (TinyLlama es ideal por tamaño y velocidad)
RUN wget -O /app/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
