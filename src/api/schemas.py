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


class MailProfileSchema(BaseModel):
    id: str
    name: str
    email: str
    server: str
    upn: Optional[str] = None
    folder: str = "INBOX"
    is_active: bool = False


class MailProfileUpsertSchema(BaseModel):
    profile_id: Optional[str] = None
    profile_name: str
    exchange_user: str
    exchange_server: str
    exchange_pass: Optional[str] = None
    exchange_upn: Optional[str] = None
    exchange_folder: str = "INBOX"
    ai_threads: int = 4
    ai_temp: float = 0.1
    set_active: bool = True
