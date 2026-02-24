# Email AI Assistant - Guía de Entorno WSL y Docker

Este documento explica cómo está configurado el entorno de desarrollo y ejecución de este proyecto utilizando Windows Subsystem for Linux (WSL) y Docker.

## Arquitectura de Contenedores

El proyecto `Entrenar_IA_correos` consta de múltiples servicios empaquetados en contenedores Docker para garantizar escalabilidad y un aislamiento limpio de dependencias:

1. **`postgres_vectordb`**: Base de datos PostgreSQL con extensión `pgvector` que aloja la Knowledge Base y permite búsquedas semánticas (RAG).
2. **`llm_service`**: Microservicio en FastAPI que expone el modelo LLM cuantizado (TinyLlama en 4 bits) usando PyTorch y adaptadores (LoRA).
3. **`email_app`**: La aplicación principal en Python (`proyecto_email_ai`) que se conecta a Exchange, consulta la base de datos RAG, y solicita la generación de respuestas al modelo LLM.

## Configuración y Trabajo con WSL

Dado que estás desarrollando en Windows pero usando contenedores a través de WSL2 (Debian), **no es necesario mover ni copiar los archivos del proyecto adentro del sistema de archivos interno de Debian**.

### ¿Cómo funciona el acceso a archivos?

WSL2 monta automáticamente las unidades de disco de Windows.
Tu código fuente, que reside en:
`D:\02_DESARROLLO\Entrenar_IA_correos`

Aparece automáticamente en WSL dentro del directorio `/mnt/`:
`/mnt/d/02_DESARROLLO/Entrenar_IA_correos`

### Pasos para iniciar o detener los contenedores

Todas las ejecuciones de Docker deben hacerse preferiblemente desde la terminal de **WSL (Debian)** apuntando al directorio montado.

1. Abre tu terminal de Debian (en Windows Terminal, presiona `Ctrl+Shift+T` y elige Debian, o ejecuta el comando `debian` en tu terminal).
2. Navega al directorio del proyecto:
   ```bash
   cd /mnt/d/02_DESARROLLO/Entrenar_IA_correos
   ```
3. Ejecuta Docker Compose en segundo plano (detached mode):
   ```bash
   docker compose up -d --build
   ```
4. Para detener los contenedores sin borrar sus volúmenes (manteniendo la base de datos intacta):
   ```bash
   docker compose stop
   ```
5. Para bajar los contenedores y eliminarlos por completo (borrará redes temporales, útil para limpiar al finalizar, pero requiere que configures persistencia si quieres mantener datos en `/var/lib/postgresql/data` del host):
   ```bash
   docker compose down
   ```

## Volúmenes y Sincronización

`docker-compose.yml` está configurado para utilizar "bind mounts":

```yaml
    volumes:
      - ./proyecto_email_ai:/app
      - ./config:/app/config
```

Esto significa que **cualquier cambio** que hagas en el código de tu aplicación principal (`proyecto_email_ai/...` o en `config/`) a través de Visual Studio Code en Windows, **se reflejará instantáneamente dentro del contenedor** `email_app` y `llm_service`, sin necesidad de reconstruir (`--build`) la imagen de Docker a cada rato, agilizando enormemente el desarrollo.

## Variables de Entorno

Toda configuración sensible (usuarios y contraseñas de Base de Datos y de Exchange) se gestiona a través de un archivo oculto `.env` situado en la raíz (`D:\02_DESARROLLO\Entrenar_IA_correos\.env`).

Si tus credenciales cambian en el futuro, edita directamente este archivo. Docker inyectará esas variables de forma segura dentro de los contenedores que las requieran en tiempo de ejecución.
