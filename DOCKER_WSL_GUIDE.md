# Ejecución con Docker en WSL/Debian

## Estructura del Proyecto (Refactorizado)

```
src/
├── main.py                  # Punto de entrada FastAPI (52 líneas - muy limpio)
├── app_state.py             # Estado global compartido
├── api/
│   ├── routes.py           # Todos los endpoints REST
│   └── schemas.py          # Modelos Pydantic
├── core/
│   └── security.py         # Funciones de seguridad
├── infrastructure/          # Adaptadores externos
│   ├── database/postgres.py # PostgreSQL + pgvector
│   └── exchange/connector.py # Exchange API
├── domain/                  # Lógica pura sin dependencias
│   ├── email/processor.py
│   ├── ai/responder.py
│   └── knowledge/embedder.py
├── services/                # Orquestación de casos de uso
│   ├── email_service.py
│   ├── config_service.py
│   ├── knowledge_service.py
│   └── workflow_service.py
└── static/                  # Frontend (index.html, etc)
```

## Levantar Servicios en Docker

### 1. Construir imágenes
```bash
docker compose build
```

### 2. Iniciar servicios
```bash
docker compose up -d
```

### 3. Verificar servicios
```bash
docker compose ps
```

## Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `email_app` | 8080 | API principal (FastAPI) |
| `llm_service` | 8000 | Modelo LLM (TinyLlama en 4-bit) |
| `postgres_vectordb` | 5432 | BD + pgvector (RAG) |

## Verificar Conectividad

### Desde WSL
```bash
# Probar API principal
curl http://localhost:8080/api/health

# Probar LLM
curl http://localhost:8000/health

# Probar BD
psql -h localhost -U email_ai_user -d knowledge_base -c "SELECT version();"
```

## Logs

```bash
# Logs del contenedor email_app
docker logs -f email_ai_app

# Logs del contenedor LLM
docker logs -f email_ai_llm

# Logs de BD
docker logs -f email_ai_postgres
```

## Variables de Entorno (.env)

```env
# Exchange
EXCHANGE_USER=tu_email@empresa.com
EXCHANGE_PASS=tu_contraseña_encriptada
EXCHANGE_SERVER=outlook.office365.com
EXCHANGE_UPN=tu_upn@empresa.com

# Base de Datos
DB_HOST=postgres_vectordb
DB_PORT=5432
DB_NAME=knowledge_base
DB_USER=email_ai_user
DB_PASS=super_secreto

# LLM
LLM_API_URL=http://llm_service:8000

# Seguridad
SECRET_KEY=tu_clave_secreta_aqui
```

## Ejecutar Tests en Docker

```bash
# Test de conexiones
docker exec email_ai_app python tests/test_connections.py

# Test de Exchange
docker exec email_ai_app pytest tests/test_exchange.py -v

# Diagnóstico de emails
docker exec email_ai_app python tests/diagnostico_emails.py
```

## Troubleshooting

### Problema: "Connection refused" a PostgreSQL
```bash
# Verificar que el contenedor esté corriendo
docker ps | grep postgres

# Revisar logs
docker logs email_ai_postgres
```

### Problema: "ModuleNotFoundError" en src
```bash
# Asegurar que PYTHONPATH incluya /app
docker exec email_ai_app env | grep PYTHON

# Si no funciona, ejecutar directamente:
docker exec -e PYTHONPATH=/app email_ai_app python -c "from src.main import app; print('OK')"
```

### Problema: Puerto 8080 en uso
```bash
# Cambiar puerto en docker-compose.yml
# Cambiar "8080:8080" a "8081:8080"
# O matar el proceso que usa 8080:
lsof -ti:8080 | xargs kill -9
```

## Tips para Desarrollo en WSL

### 1. Recargar código sin rebuild
El Dockerfile monta volúmenes para desarrollo:
```bash
# Editar código en Windows/WSL
# El contenedor verá los cambios inmediatamente
# Solo necesitas reiniciar si cambias imports o estructuras
docker compose restart email_ai_app
```

### 2. Acceder a shell del contenedor
```bash
docker exec -it email_ai_app /bin/bash

# Dentro del contenedor:
cd /app
python -m pytest tests/ -v
```

### 3. Limpiar todo
```bash
# Parar servicios
docker compose down

# Borrar volúmenes (BD se reseteará)
docker compose down -v

# Borrar imágenes
docker rmi email_ai_app email_ai_llm
```

## GPU en WSL (NVIDIA)

Si tienes NVIDIA Container Toolkit instalado:

1. Descomenta en docker-compose.yml:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

2. Reiniciar servicios:
```bash
docker compose down
docker compose up -d
```

## Referencias

- [Docker en WSL](https://docs.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers)
- [Docker Compose](https://docs.docker.com/compose/)
- [FastAPI Production](https://fastapi.tiangolo.com/deployment/)
