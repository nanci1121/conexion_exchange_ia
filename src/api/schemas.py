from pydantic import BaseModel
from typing import Optional, List

class EmailSchema(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    is_read: bool
    body_preview: str = ""
    
class EmailDetailSchema(EmailSchema):
    body: str
    ai_response: Optional[str] = None
    status: str = "PENDIENTE"

class SettingSchema(BaseModel):
    key: str
    value: str
