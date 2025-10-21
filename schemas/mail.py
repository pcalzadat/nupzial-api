# schemas/mail.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class AttachmentIn(BaseModel):
    name: str
    content_type: str
    content_base64: str  # Base64

class SendEmailIn(BaseModel):
    to: List[EmailStr]
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    save_to_sent_items: bool = True
    attachments: Optional[List[AttachmentIn]] = None
