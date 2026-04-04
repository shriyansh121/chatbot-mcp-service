from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.db.session import SessionLocal
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.schemas.chat import ChatRequest, ChatResponse, SessionResponse, MessageResponse
from app.dependencies.auth import get_current_user
from app.db.models.user import User
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

chat_service = ChatService()

class RenameRequest(BaseModel):
    title: str

@router.post("/message")
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Streaming response using the generator from ChatService
    return StreamingResponse(
        chat_service.process_message_stream(db, current_user.id, request),
        media_type="text/event-stream"
    )

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = SessionService.get_user_sessions(db, current_user.id)
    return [SessionResponse.from_orm(session) for session in sessions]

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = SessionService.get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages for this session
    messages = SessionService.get_session_messages(db, session_id, current_user.id)
    session.messages = messages
    
    return SessionResponse.from_orm(session)

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = SessionService.create_session(db, current_user.id)
    return SessionResponse.from_orm(session)

@router.put("/sessions/{session_id}/rename")
async def rename_session(
    session_id: UUID,
    request: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = SessionService.rename_session(db, session_id, current_user.id, request.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session renamed successfully", "title": request.title}

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = SessionService.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}