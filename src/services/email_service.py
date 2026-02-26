import asyncio
import logging
from typing import Optional
from ..infrastructure.exchange.connector import get_paginated_emails, get_email_details, save_draft, mark_as_read, delete_email
from ..infrastructure.database.postgres import get_emails_from_db, get_email_detail_db, delete_email_db, update_email_status
from ..domain.ai.responder import AIResponder
from ..domain.knowledge.embedder import search_knowledge
from ..app_state import app_state

logger = logging.getLogger("EmailService")

async def list_emails(offset: int = 0, limit: int = 10):
    """List emails from database with pagination"""
    data = await asyncio.to_thread(get_emails_from_db, offset, limit)
    return data

async def get_email_detail(item_id: str):
    """Get email detail from DB or Exchange"""
    detail = await asyncio.to_thread(get_email_detail_db, item_id)
    
    # If not in DB or body is empty, fetch from Exchange
    if not detail or not detail.get('body'):
        logger.info(f"Fetching body for {item_id} from Exchange")
        detail = await asyncio.to_thread(get_email_details, item_id)
    return detail

async def generate_answer(
    item_id: str,
    custom_prompt: Optional[str] = None,
    language: str = 'es'
) -> dict:
    """Generate AI response for an email using RAG (Retrieval Augmented Generation)"""
    # Get the email
    detail = await get_email_detail(item_id)
    
    if not detail:
        return {"status": "error", "message": "Email not found"}
    
    # Search knowledge base for relevant context
    email_content = detail.get('body', '') + " " + detail.get('subject', '')
    knowledge_results = await asyncio.to_thread(search_knowledge, email_content, top_k=3)
    
    # Build context from knowledge base
    context_text = ""
    if knowledge_results:
        logger.info(f"Found {len(knowledge_results)} relevant knowledge fragments")
        context_text = "\n\nCONTEXTO DE LA BASE DE CONOCIMIENTO:\n"
        for idx, (content, filename, similarity) in enumerate(knowledge_results, 1):
            context_text += f"\n[Documento {idx}: {filename} - Relevancia: {similarity:.2f}]\n{content}\n"
    else:
        logger.info("No relevant knowledge found in database")
    
    # Prepare prompt
    ai = AIResponder()
    instructions = custom_prompt or "Responde de forma profesional, cordial y breve."
    
    lang_text = {
        "es": "español",
        "en": "inglés",
        "both": "español e inglés (ambos)"
    }.get(language, "español")

    raw_prompt = (
        f"TAREA: Escribir respuesta en {lang_text}.\n"
        f"INSTRUCCIÓN: {instructions}\n"
        f"{context_text}\n"
        f"CORREO DE {detail['sender']}:\n"
        f"{detail.get('body', '')}"
    )

    # Update dashboard state
    app_state["current_email"] = {
        "subject": detail["subject"],
        "sender": detail["sender"],
        "date": detail["date"]
    }
    app_state["status"] = "Generando respuesta con RAG..."

    # Generate response
    ai_response = await asyncio.to_thread(ai.generate_response, raw_prompt, 'generation')
    
    # Save to DB
    if ai_response:
        await asyncio.to_thread(update_email_status, item_id, 'PROCESADO', ai_response)
        app_state["emails_processed"] += 1
        
    app_state["current_email"] = None
    app_state["status"] = "En espera (Dashboard)"
        
    return {"status": "success", "ai_response": ai_response}

async def save_draft_email(item_id: str, body: str):
    """Save email draft"""
    if not body:
        return {"status": "error", "message": "No body provided"}
    
    success = await asyncio.to_thread(save_draft, item_id, body)
    return {"status": "success" if success else "error"}

async def mark_email_as_read(item_id: str, read: bool = True):
    """Mark email as read/unread"""
    success = await asyncio.to_thread(mark_as_read, item_id, read)
    return {"status": "success" if success else "error"}

async def delete_email_async(item_id: str):
    """Delete email from both Exchange and local DB"""
    success_ex = await asyncio.to_thread(delete_email, item_id)
    success_db = await asyncio.to_thread(delete_email_db, item_id)
    
    return {"status": "success" if (success_ex and success_db) else "partial_success"}
