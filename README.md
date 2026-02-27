# 📧 Email AI - Asistente Inteligente de Correos

[![CI - Validación y Tests](https://github.com/nanci1121/conexion_exchange_ia/actions/workflows/ci.yml/badge.svg)](https://github.com/nanci1121/conexion_exchange_ia/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema de automatización de respuestas de correo electrónico con inteligencia artificial, integración con Exchange y búsqueda aumentada por recuperación (RAG).

## 🚀 Características

- **RAG (Retrieval Augmented Generation)**: Responde correos usando tu base de conocimiento corporativa
- **Integración Exchange**: Conecta directamente con Microsoft Exchange para gestionar correos
- **LLM Local**: Modelo de lenguaje Llama 3.2 3B GGUF Q4 (sin requerir API externa)
- **Base de Conocimiento**: Indexa PDF, DOCX, TXT con búsqueda vectorial (pgvector)
- **Dashboard Web**: Interfaz moderna y responsive en tiempo real
- **Contenedores Docker**: Despliegue completo con docker-compose

## 📋 Requisitos Previos

### Sistema
- Windows 10/11 con WSL2 o Linux/macOS
- Docker Desktop con soporte WSL2
- 8GB RAM mínimo (16GB recomendado)
- 30GB espacio disco disponible

### Software
- Python 3.9+
- Git
- Docker & Docker Compose
- (Opcional) PostgreSQL cliente para debugging

## 🔧 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/nanci1121/conexion_exchange_ia.git
cd conexion_exchange_ia
```

### 2. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto:

```env
# Exchange Configuration
EXCHANGE_URL=https://outlook.office365.com/EWS/Exchange.asmx
EXCHANGE_EMAIL=tu_email@empresa.com
EXCHANGE_PASSWORD=tu_contraseña
EXCHANGE_FOLDER=INBOX

# Database Configuration
DB_USER=email_ai_user
DB_PASS=super_secreto
DB_HOST=postgres_vectordb
DB_PORT=5432
DB_NAME=knowledge_base

# LLM Service
LLM_API_URL=http://llm_service:8000
LLM_MODEL=Llama-3.2-3B-Instruct

# App Configuration
APP_HOST=0.0.0.0
APP_PORT=8080
ENVIRONMENT=production
```

### 3. Levantar contenedores (primera vez)

⚠️ **IMPORTANTE: La primera ejecución descargará el modelo LLM (~2.5GB). Puede tomar 20-30 minutos.**

```bash
docker-compose up --build
```

**Qué sucede automáticamente:**
1. ✅ Se descarga `Llama-3.2-3B-Instruct-Q4_K_M.gguf` desde HuggingFace (dentro del contenedor)
2. ✅ Se monta en `./llm_service/models/` en tu máquina
3. ✅ Se construyen todas las imágenes Docker
4. ✅ Se levantan 3 contenedores: app, LLM, base de datos

**Espera a ver este mensaje:**
```
✔ Container email_ai_app      Running
✔ Container email_ai_llm      Running
✔ Container email_ai_postgres Running
```

Para futuras ejecuciones (mucho más rápidas):
```bash
docker-compose up
```

### 4. Verificar que todo funciona

```bash
# Verificar contenedores activos
docker ps

# Verificar que el LLM repsonde
curl http://localhost:8000/health

# Verificar que la app repsonde
curl http://localhost:8080
```

Deberías recibir:
- **LLM health**: `{"status":"ok","technology":"GGUF/llama.cpp","model":"..."}`
- **App**: Código HTTP 200

### 5. Acceder a la aplicación

Abre en tu navegador: **http://localhost:8080**

🎉 **¡Ya está funcionando!**

---

## 📚 Documentación del Modelo LLM

Para detalles sobre la descarga, requisitos, troubleshooting y GPU support, ve a:

**[llm_service/models/README.md](llm_service/models/README.md)**

## 📖 Uso

### Dashboard Principal
- **Estadísticas**: Correos procesados, estado del LLM, latencia, conexión Exchange
- **Actividad Reciente**: Feed en tiempo real de correos procesados
- **Estado del Sistema**: Verificación de conectividad a todos los servicios

### Pestaña "Correos"
1. **Listar correos**: Ve todos los correos en tu bandeja
2. **Generar respuesta**: Selecciona un correo y elige modo:
   - **Generación estándar**: Prompt automático profesional
   - **Custom**: Proporciona instrucciones personalizadas
3. **Seleccionar idioma**: Responde en español, inglés o ambos
4. **Guardar borrador**: Guarda la respuesta sin enviar

### Pestaña "Conocimiento" (RAG)
1. **Subir documentos**:
   - Arrastra archivos PDF, DOCX, TXT
   - Máximo 10MB por archivo
   - Se indexan automáticamente con embeddings

2. **Documentos indexados**:
   - Visualiza todos los documentos cargados
   - Ver fecha de indexación
   - Eliminar documentos si es necesario

3. **Cómo funciona el RAG**:
   ```
   Correo → Búsqueda de documentos relevantes → 
   Contexto + Correo → LLM → Respuesta mejorada
   ```

## 🏗️ Arquitectura

```
src/
├── api/                      # Rutas FastAPI
│   ├── routes.py            # Endpoints REST
│   └── schemas.py           # Modelos Pydantic
├── domain/                   # Lógica de negocio
│   ├── ai/
│   │   └── responder.py      # Comunicación con LLM
│   ├── email/
│   │   └── processor.py      # Procesamiento de correos
│   └── knowledge/
│       └── embedder.py       # Indexación y búsqueda RAG
├── infrastructure/           # Acceso a recursos externos
│   ├── database/
│   │   └── postgres.py       # Conexión PostgreSQL + pgvector
│   └── exchange/
│       └── connector.py      # API de Microsoft Exchange
├── services/                 # Orquestación
│   ├── email_service.py      # Lógica completa de correos (CON RAG)
│   ├── knowledge_service.py  # Gestión documentos
│   ├── config_service.py     # Configuración
│   └── workflow_service.py    # Workflows
├── static/                   # Frontend
│   ├── index.html           # Interfaz web
│   ├── script.js            # Lógica JavaScript
│   └── style.css            # Estilos (tema oscuro/claro)
├── main.py                   # Punto de entrada FastAPI
├── app_state.py              # Estado global compartido
└── core/
    └── security.py           # Autenticación/autorización

data/
├── knowledge_base/           # Documentos para RAG
│   ├── politica_seguridad.txt
│   ├── faq_tecnico.txt
│   └── info_empresa.txt
├── templates/               # Prompts de ejemplo
└── training/                # Datasets de entrenamiento

config/
├── config.yaml              # Configuración LLM, tareas
├── exchange.yaml            # Settings Exchange
└── model_config.yaml        # Parámetros del modelo
```

## 🔌 API REST

### Correos
```bash
GET /api/emails                    # Listar correos (paginado)
GET /api/email/{id}                # Detalles correo
POST /api/email/{id}/generate      # Generar respuesta con RAG
POST /api/email/{id}/draft         # Guardar borrador
DELETE /api/email/{id}             # Eliminar correo
PATCH /api/email/{id}/status       # Actualizar estado
```

### Conocimiento (RAG)
```bash
GET /api/knowledge                 # Listar documentos indexados
POST /api/knowledge/upload         # Subir documento (indexa automáticamente)
GET /api/knowledge/search          # Buscar en base de conocimiento
DELETE /api/knowledge/{doc_id}     # Eliminar documento
```

### Sistema
```bash
GET /api/health                    # Estado general
GET /api/status                    # Estado servicios (DB, LLM, Exchange)
GET /api/config                    # Configuración actual
```

## 🔒 Seguridad

### Política de Seguridad Integrada
- Contraseñas: Mínimo 12 caracteres, renovación cada 90 días
- MFA obligatoria para sistemas críticos
- Autenticación con credenciales Exchange
- Datos confidenciales cifrados en tránsito (HTTPS)
- Base de datos con pgvector para privacidad vectorial

Consulta [data/knowledge_base/politica_seguridad.txt](data/knowledge_base/politica_seguridad.txt) para más detalles.

## 🐳 Docker

### Servicios incluidos

#### 1. **email_ai_app** (FastAPI - Puerto 8080)
- Aplicación web principal
- Orquesta lógica de negocio
- Sirve frontend estático

#### 2. **email_ai_llm** (FastAPI + Llama 3.2 3B GGUF - Puerto 8000)
- Modelo Llama 3.2 3B cuantizado en Q4 (~2.5GB)
- API para generación de texto con llama.cpp
- Sin dependencias de APIs externas, solo CPU

#### 3. **email_ai_postgres** (pgvector - Puerto 5432)
- Base de datos vectorial
- Indexa embeddings de documentos
- Búsqueda por similitud coseno

### Comandos útiles
```bash
# Levantar todo
docker-compose up -d

# Ver logs
docker-compose logs -f email_ai_app      # Logs de la app
docker-compose logs -f email_ai_llm      # Logs del LLM

# Parar servicios
docker-compose down

# Limpiar volúmenes (CUIDADO: borra datos)
docker-compose down -v

# Reconstruir imágenes
docker-compose up -d --build
```

## 🛠️ Configuración

### config.yaml
```yaml
model:
  name: Llama-3.2-3B-Instruct
  device: cpu
  quantization: Q4_K_M GGUF
  context_window: 4096
  max_tokens: 256
  temperature: 0.1
  top_p: 0.9
  
  tasks:
    generation:
      temperature: 0.1
      max_tokens: 256
    classification:
      temperature: 0.3
      max_tokens: 50
```

### exchange.yaml
```yaml
server:
  url: https://outlook.office365.com/EWS/Exchange.asmx
  timeout: 30
  
folders:
  inbox: INBOX
  drafts: DRAFTS
  sent: SENT ITEMS
```

## 📊 Base de Datos

### Schema principal
```sql
-- Tabla de documentos indexados
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  filename TEXT,
  content TEXT,
  embedding vector(384),  -- all-MiniLM-L6-v2 (384 dims)
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de correos procesados
CREATE TABLE emails (
  id VARCHAR(255) PRIMARY KEY,
  subject TEXT,
  sender TEXT,
  body TEXT,
  status VARCHAR(50),
  ai_response TEXT,
  created_at TIMESTAMP,
  processed_at TIMESTAMP DEFAULT NOW()
);
```

## 🚨 Troubleshooting

### "Conexión a Exchange fallida"
```
Verifica:
1. Credenciales en .env correctas
2. Exchange URL accesible (sin proxy)
3. Permisos de acceso a EWS habilitados
4. MFA desactivado o configurado (solo contraseña para EWS)
```

### "Error indexando documento"
```
Posibles causas:
1. Archivo corrupto o no soportado
2. Modelo de embeddings no cargado
3. PostgreSQL no disponible
4. Documento > 10MB

Solución: Verifica logs de email_ai_app
```

### "LLM tarda mucho o no responde"
```
1. Verifica recurso CPU/memoria: docker stats
2. Reinicia contenedor: docker restart email_ai_llm
3. Aumenta timeouts en .env
4. Con GPU: usa nvidia-docker en docker-compose
```

### "RAG no retorna documentos relevantes"
```
1. Verifica documentos cargados: GET /api/knowledge
2. Prueba búsqueda: GET /api/knowledge/search?q=test
3. Sube más documentos para mejor contexto
4. Ajusta top_k en email_service.py (ahora 3)
```

## 🎯 Plan de Desarrollo

- [ ] Autenticación LDAP/AD corporativa
- [ ] Integración con Slack/Teams para notificaciones
- [ ] Fine-tuning del modelo con correos históricos
- [ ] Traducción automática multiidioma
- [ ] Historial de versiones de respuestas
- [ ] Analytics y reportes
- [ ] Webhook para eventos
- [ ] Soporte para múltiples depósitos Exchange

## 📞 Soporte

### Documentación
- [Guía Docker WSL](DOCKER_WSL_GUIDE.md)
- [FAQ Técnico](data/knowledge_base/faq_tecnico.txt)
- [Política de Seguridad](data/knowledge_base/politica_seguridad.txt)

### Contacto
- **Issues**: https://github.com/nanci1121/conexion_exchange_ia/issues
- **Autor**: [nanci1121]
- **Email**: (configurar en proyecto)

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/mejora`)
3. Commit cambios (`git commit -m 'feat: descripción'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Abre un Pull Request

## 📜 Changelog

### v1.0.0 (26 Feb 2026)
- ✅ Integración RAG completa
- ✅ Arquitectura escalable (domain-driven)
- ✅ 3 documentos de ejemplo
- ✅ Dashboard web funcional
- ✅ Sistema limpio y optimizado
- ✅ Documentación completa

---

**Última actualización**: 26 de febrero de 2026  
**Estado**: 🟢 En Producción
