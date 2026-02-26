from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os

from ..services import email_service, config_service, knowledge_service
from ..app_state import app_state

router = APIRouter()

# =========== Schemas ===========

class EmailSendRequest(BaseModel):
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    item_id: str
    custom_prompt: Optional[str] = None
    language: Optional[str] = 'es'

class ConfigRequest(BaseModel):
    exchange_user: str
    exchange_pass: Optional[str] = None
    exchange_server: str
    exchange_upn: Optional[str] = None
    ai_threads: int
    ai_temp: float

# =========== General Routes ===========

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve main dashboard"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        dashboard_file = static_dir / "index.html"
        
        if dashboard_file.exists():
            with open(dashboard_file, "r") as f:
                return f.read()
        else:
            return "<h1>Email AI Dashboard</h1><p>Frontend not available (index.html not found)</p>"
    except Exception as e:
        return f"<h1>Email AI Dashboard</h1><p>Error loading dashboard: {str(e)}</p>"

@router.get("/api/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "email_app_api"}

@router.get("/api/status")
async def get_status():
    """Get application status"""
    return app_state

# =========== Email Routes ===========

@router.get("/api/emails")
async def list_emails(offset: int = 0, limit: int = 10):
    """List emails with pagination"""
    return await email_service.list_emails(offset, limit)

@router.get("/api/emails/{item_id:path}")
async def email_detail(item_id: str):
    """Get email detail"""
    return await email_service.get_email_detail(item_id)

@router.post("/api/emails/generate-answer")
async def generate_answer(req: EmailSendRequest):
    """Generate AI response for email"""
    return await email_service.generate_answer(
        req.item_id,
        req.custom_prompt,
        req.language
    )

@router.post("/api/emails/save-draft")
async def save_draft(req: EmailSendRequest):
    """Save email draft"""
    return await email_service.save_draft_email(req.item_id, req.body)

@router.patch("/api/emails/{item_id:path}/read")
async def mark_as_read(item_id: str, read: bool = True):
    """Mark email as read/unread"""
    return await email_service.mark_email_as_read(item_id, read)

@router.delete("/api/emails/{item_id:path}")
async def delete_email(item_id: str):
    """Delete email"""
    return await email_service.delete_email_async(item_id)

# =========== Config Routes ===========

@router.get("/api/config")
async def get_config():
    """Get current configuration"""
    return await config_service.get_config()

@router.post("/api/config")
async def update_config(req: ConfigRequest):
    """Update configuration"""
    return await config_service.update_config(
        req.exchange_user,
        req.exchange_server,
        req.exchange_pass,
        req.exchange_upn,
        req.ai_threads,
        req.ai_temp
    )

# =========== Knowledge Routes ===========

@router.get("/api/knowledge")
async def list_knowledge():
    """List knowledge documents"""
    return await knowledge_service.list_knowledge_documents()

@router.post("/api/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload knowledge document"""
    # Create temp_uploads directory safely (works in containers and locally)
    temp_dir = Path.cwd() / "temp_uploads"
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    file_path = str(temp_dir / file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return await knowledge_service.upload_knowledge_document(file_path, file.filename)
