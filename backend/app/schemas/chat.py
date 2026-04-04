from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class MessageCreate(BaseModel):
    content: str
    role: str = "user"

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SessionCreate(BaseModel):
    title: Optional[str] = None

class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str]
    is_archived: bool
    created_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None
    edit_mode: Optional[bool] = False
    regenerate: Optional[bool] = False

class ChatResponse(BaseModel):
    message: str
    session_id: UUID
    route_type: str  # "simple" or "gcp"