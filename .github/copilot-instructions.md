# Project Guidelines

## Scope
Estas instrucciones aplican a todo el workspace.
Prioriza cambios pequenos, seguros y faciles de revisar.

## Code Style
- Usa Python 3.9+ y tipado cuando aporte claridad en fronteras de API y servicios.
- Manten funciones enfocadas y evita mezclar acceso a infraestructura con logica de dominio.
- Conserva nombres y estructura existente en `src/` salvo que el cambio pida refactor explicito.
- Evita cambios cosmeticos no relacionados con la tarea.

## Architecture
- Respeta las capas actuales:
  - `src/api/`: contratos HTTP (rutas y schemas)
  - `src/domain/`: logica de negocio pura
  - `src/infrastructure/`: integraciones externas (Exchange, Postgres)
  - `src/services/`: orquestacion entre capas
- No mover responsabilidades entre capas sin justificar impacto y plan de migracion.

## Build and Test
- Para entorno local rapido: `python -m pytest tests -q`.
- Si el cambio toca integraciones, prioriza tests objetivo en `tests/` y documenta limites si dependen de servicios externos.
- Si no puedes ejecutar pruebas, dilo explicitamente en el resumen final.

## Conventions
- En cambios de API, valida compatibilidad de payloads en `src/api/schemas.py`.
- En cambios de flujo de correos, revisa impacto en `src/services/email_service.py` y `src/services/workflow_service.py`.
- En cambios RAG, verifica consistencia entre `src/domain/knowledge/embedder.py` y `src/services/knowledge_service.py`.
- Mantener secretos fuera del codigo; usa `.env` y archivos de `config/`.

## Documentation
- Para operacion Docker/WSL, referencia `README_WSL_DOCKER.md` y `docs/comandos_docker.md`.
- Para arquitectura general y endpoints, referencia `README.md`.
