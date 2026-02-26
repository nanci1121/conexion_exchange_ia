# Estado global compartido entre FastAPI y el motor de processing
app_state = {
    "status": "Iniciando...",
    "exchange_connected": False,
    "emails_processed": 0,
    "emails": [],
    "current_email": None,
    "last_error": None,
    "active_tasks": []
}
