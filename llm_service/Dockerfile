
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

# Llama-3.2-3B es mucho más potente y tiene mejor manejo de instrucciones que TinyLlama
RUN wget -O /app/models/llama-3.2-3b-instruct-q4_k_m.gguf https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
