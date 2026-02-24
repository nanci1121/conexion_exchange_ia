from fastapi import APIRouter
import os
import yaml
from .exchange_connector import test_connection, get_latest_emails

router = APIRouter(prefix="/api/emails", tags=["Emails"])

@app.get("/api/emails/latest")
async def get_emails():
    # Esta es una ruta temporal, la integraremos mejor en main.py
    # Por ahora vamos a modificar main.py directamente para que sea más limpio
    pass
