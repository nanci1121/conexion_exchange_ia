# Modelos LLM - Llama 3.2 3B GGUF

## 🚀 TL;DR - Funcionamiento Automático

**No tienes que hacer nada manualmente.** El modelo se descarga automáticamente cuando ejecutas:

```bash
docker-compose up --build
```

El `Dockerfile` contiene instrucciones para:
1. Crear esta carpeta `/app/models` dentro del contenedor
2. Descargar automáticamente `llama-3.2-3b-instruct-q4_k_m.gguf` desde HuggingFace
3. Montarla en `./llm_service/models` en tu máquina (host)

## 📦 Lo que sucede automáticamente

### Durante `docker-compose up --build`:

```dockerfile
# Dockerfile descarga y monta el modelo:
RUN mkdir -p /app/models
RUN wget -O /app/models/llama-3.2-3b-instruct-q4_k_m.gguf \
    https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

### Volumen compartido:

```yaml
# docker-compose.yml:
volumes:
  - ./llm_service/models:/app/models  # Host ↔ Contenedor
```

## ⚙️ Estructura de carpetas

```
llm_service/
├── Dockerfile                          # Descarga el modelo automáticamente
├── app.py                              # API FastAPI + llama.cpp
├── requirements.txt                    # Dependencias (llama-cpp-python)
└── models/
    ├── README.md                       # Este archivo
    └── llama-3.2-3b-instruct-q4_k_m.gguf  # SE DESCARGA AUTOMÁTICAMENTE (~2.5GB)
```

## 📥 Primera ejecución

### Paso 1: Clonar repositorio
```bash
git clone https://github.com/nanci1121/conexion_exchange_ia.git
cd conexion_exchange_ia
```

### Paso 2: Construir con Docker
```bash
docker-compose up --build
```

**Esto hará:**
- ✅ Construir imagen `email_ai_llm`
- ✅ Descargar `llama-3.2-3b-instruct-q4_k_m.gguf` (~2.5GB) - TARDA 10-30 MIN
- ✅ Montar en `./llm_service/models/`
- ✅ Iniciar servicio en puerto 8000

**Tiempo estimado:**
- Primera vez: 10-30 minutos (descarga + construcción)
- Siguientes: 1-2 minutos (usa imagen cacheada)

### Paso 3: Verificar que funciona
```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "technology": "GGUF/llama.cpp",
  "model": "TinyLlama-1.1B"
}
```

## 🔄 Después de la primera descarga

El archivo `.gguf` estará en tu disco en:

**Windows:**
```
d:\02_DESARROLLO\Entrenar_IA_correos\llm_service\models\llama-3.2-3b-instruct-q4_k_m.gguf
```

**Linux/Mac:**
```
./llm_service/models/llama-3.2-3b-instruct-q4_k_m.gguf
```

### Comportamiento del volumen:

- ✅ **Primera vez**: Se descarga dentro del contenedor → se copia al host
- ✅ **Siguientes veces**: El contenedor reutiliza el archivo del host (más rápido)
- ✅ **Persistencia**: El archivo se mantiene entre reinicios

## 📊 Especificaciones del modelo

| Propiedad | Valor |
|-----------|-------|
| **Nombre** | Llama 3.2 3B Instruct |
| **Tamaño** | ~2.5GB (ya cuantizado en Q4_K_M) |
| **Contexto** | 128K tokens (configurado a 4K en app.py) |
| **Cuantización** | Q4_K_M (4-bit, excelente balance precisión/velocidad) |
| **Precisión** | ~95-98% vs modelo original fp32 |
| **Velocidad CPU** | ~10-15 tokens/segundo (4 threads) |
| **Velocidad GPU** | ~100-150 tokens/segundo (si dispones de NVIDIA) |
| **RAM requerida** | 8GB mínimo (16GB recomendado) |
| **Descarga** | <https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF> |

## 🆘 Troubleshooting

### "Descarga muy lenta"

1. **Verifica tu conexión**: Download desde HuggingFace tarda más en ciertos horarios
2. **Espera**: Primera descarga puede tomar 20-30 minutos con conexión lenta
3. **Reintentar**: Si se corta, `docker-compose up --build` retoma desde donde quedó

### "Model not found" o error en app.py

```bash
# Verifica que existe:
ls -la llm_service/models/llama-3.2-3b-instruct-q4_k_m.gguf

# Si no existe o está incompleto, limpia y reconstruye:
docker-compose down
rm -rf llm_service/models/*.gguf
docker-compose up --build
```

### "Out of memory" durante descarga

Si tienes <8GB RAM libre:
```bash
# Libera RAM cerrando otras aplicaciones
# Luego reintenta:
docker-compose up --build
```

### "Build fallido en wget"

Si HuggingFace tiene tiempo de espera:
1. Intenta de nuevo: `docker-compose up --build`
2. Usa mirror alternativo en Dockerfile:
   ```dockerfile
   RUN wget -O /app/models/llama-3.2-3b-instruct-q4_k_m.gguf \
       https://huggingface.co/TheBloke/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
   ```

## 🚀 GPU Support (Opcional)

Si tienes NVIDIA GPU, descomenta en `docker-compose.yml`:

```yaml
llm_service:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Luego reconstruye:
```bash
docker-compose up --build
```

Ganancia de velocidad: **~50-100x más rápido** que CPU.

## 📝 Nota sobre .gitignore

El archivo `.gguf` **NO** debe commitarse al repositorio:

```gitignore
# Archivo generado/descargado automáticamente
llm_service/models/*.gguf
```

Ya está configurado en el `.gitignore` del proyecto.

## ✅ Checklist de despliegue

- [ ] Clonaste el repositorio
- [ ] Tienes Docker Desktop con WSL2 (Windows) o Docker Engine (Linux/Mac)
- [ ] Ejecutaste `docker-compose up --build`
- [ ] Esperaste a que descargue el modelo (~20-30 min)
- [ ] Verificaste `/health` con curl o navegador
- [ ] Accediste a http://localhost:8080 (Email AI Dashboard)
- [ ] Subiste documentos en la pestaña "Conocimiento"
- [ ] Probaste generando respuestas a correos de prueba

¡Listo! Ya puedes empezar a usar Email AI con RAG. 🚀

