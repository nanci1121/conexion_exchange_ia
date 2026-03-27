
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

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
