# Estado global compartido entre FastAPI y el motor de processing
app_state = {
    "status": "Iniciando...",
    "exchange_connected": False,
    "exchange_user": None,
    "active_profile_id": None,
    "active_profile_name": None,
    "emails_processed": 0,
    "emails": [],
    "current_email": None,
    "last_error": None,
    "active_tasks": []
}
