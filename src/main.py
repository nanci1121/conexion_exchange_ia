import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

# Importar el motor de trabajo (usaremos una versión modificada para que sea una tarea de asyncio)
from .workflow_engine import main_loop

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmailAI-API")

# Estado global simple para mostrar en el dashboard
app_state = {
    "status": "Iniciando...",
    "exchange_connected": False,
    "emails_processed": 0,
    "emails": [],
    "last_error": None,
    "active_tasks": []
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar: Iniciar el loop de procesamiento en segundo plano
    # IMPORTANTE: main_loop contiene llamadas bloqueantes (síncronas) a Requests y ExchangeLib.
    # Para que FastAPI no se bloquee, lo ejecutamos en un hilo separado.
    logger.info("Iniciando motor de procesamiento en segundo plano (hilo separado)...")
    bg_task = asyncio.create_task(asyncio.to_thread(main_loop, app_state))
    yield
    # Al apagar: Cancelar tareas
    logger.info("Apagando motor de procesamiento...")
    # Como es un thread ejecutando código síncrono, cancel() no lo detendrá inmediatamente,
    # pero evitará nuevas iteraciones si el loop revisa una bandera de parada (opcional).
    bg_task.cancel()

app = FastAPI(title="Email AI Dashboard", lifespan=lifespan)

# Crear carpeta static si no existe (la llenaremos después)
os.makedirs("src/static", exist_ok=True)

# Servir archivos estáticos
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    # Por ahora servimos un HTML básico desde aquí, luego lo pasaremos a un archivo elegante
    with open("src/static/index.html", "r") as f:
        return f.read()

@app.get("/api/status")
async def get_status():
    return app_state

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "email_app_api"}
