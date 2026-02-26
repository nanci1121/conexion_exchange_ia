import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import os

# Importar el motor de trabajo y el conector de Exchange
from .workflow_engine import main_loop
from .exchange_connector import get_paginated_emails, get_email_details, save_draft, mark_as_read, delete_email
from .database import get_emails_from_db, get_email_detail_db, delete_email_db
from .ai_responder import AIResponder

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
    "current_email": None,
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

# --- Endpoints del CRUD de Correos ---

class EmailSendRequest(BaseModel):
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    item_id: str
    custom_prompt: Optional[str] = None
    language: Optional[str] = 'es'

@app.get("/api/emails")
async def list_emails(offset: int = 0, limit: int = 10):
    # Ahora consultamos la base de datos local (mucho más rápido)
    data = await asyncio.to_thread(get_emails_from_db, offset, limit)
    return data

@app.get("/api/emails/{item_id}")
async def email_detail(item_id: str):
    # Intentar primero en DB
    detail = await asyncio.to_thread(get_email_detail_db, item_id)
    
    # Si no está en DB O si está pero el cuerpo está vacío, buscar en Exchange
    if not detail or not detail.get('body'):
        logger.info(f"Cuerpo vacío en DB o no encontrado. Consultando Exchange para {item_id}")
        detail = await asyncio.to_thread(get_email_details, item_id)
    return detail

@app.post("/api/emails/generate-answer")
async def generate_answer(req: EmailSendRequest):
    # Obtener el correo (preferiblemente de DB)
    detail = await asyncio.to_thread(get_email_detail_db, req.item_id)
    if not detail:
        detail = await asyncio.to_thread(get_email_details, req.item_id)
    
    if not detail:
        return {"status": "error", "message": "Email not found"}
    
    # Preparar el prompt estructurado
    ai = AIResponder()
    instructions = req.custom_prompt or "Responde de forma profesional, cordial y breve."
    
    # Traducir el código de idioma a texto
    lang_text = "español"
    if req.language == "en": lang_text = "inglés"
    elif req.language == "both": lang_text = "español e inglés (ambos)"

    # Enviamos solo la información cruda, el servicio llm_service ya le pone el formato de chat
    raw_prompt = (
        f"TAREA: Escribir respuesta en {lang_text}.\n"
        f"INSTRUCCIÓN: {instructions}\n"
        f"CORREO DE {detail['sender']}:\n"
        f"{detail.get('body', '')}"
    )

    # Mostrar en el dashboard que estamos procesando este correo
    app_state["current_email"] = {
        "subject": detail["subject"],
        "sender": detail["sender"],
        "date": detail["date"]
    }
    app_state["status"] = "Generando respuesta..."

    ai_response = await asyncio.to_thread(ai.generate_response, raw_prompt, 'generation')
    
    # Guardar persistencia en la DB y actualizar contadores
    if ai_response:
        from .database import update_email_status
        await asyncio.to_thread(update_email_status, req.item_id, 'PROCESADO', ai_response)
        app_state["emails_processed"] += 1
        
    app_state["current_email"] = None
    app_state["status"] = "En espera (Dashboard)"
        
    return {"status": "success", "ai_response": ai_response}

@app.post("/api/emails/save-draft")
async def api_save_draft(req: EmailSendRequest):
    if not req.body:
        return {"status": "error", "message": "No body provided"}
    
    success = await asyncio.to_thread(save_draft, req.item_id, req.body)
    return {"status": "success" if success else "error"}

@app.patch("/api/emails/{item_id}/read")
async def api_mark_as_read(item_id: str, read: bool = True):
    success = await asyncio.to_thread(mark_as_read, item_id, read)
    return {"status": "success" if success else "error"}

@app.delete("/api/emails/{item_id}")
async def api_delete_email(item_id: str):
    # Intentar eliminar de Exchange
    success_ex = await asyncio.to_thread(delete_email, item_id)
    # Intentar eliminar de la base de datos local
    success_db = await asyncio.to_thread(delete_email_db, item_id)
    
    return {"status": "success" if (success_ex and success_db) else "partial_success"}
