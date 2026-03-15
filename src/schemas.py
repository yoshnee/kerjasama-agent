from typing import List, Optional
from pydantic import BaseModel


class BusinessInfoResponse(BaseModel):
    business_name: str
    avatar_initial: str
    whatsapp_number: Optional[str]
    accent_color: str
    pricing_text: Optional[str]
    services: Optional[list]
    has_services: bool


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    show_whatsapp_cta: bool
