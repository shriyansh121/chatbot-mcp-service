from sqlalchemy.orm import Session as DBSession
from app.services.session_service import SessionService
from app.core.agent import ChatAgent
from app.schemas.chat import ChatRequest, ChatResponse, MessageCreate
from app.db.models.session_table import Session
from app.db.models.message import Message
from uuid import UUID
from typing import AsyncGenerator
import json
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.agent = ChatAgent()
    
    async def process_message_stream(self, db: DBSession, user_id: UUID, request: ChatRequest) -> AsyncGenerator[str, None]:
        # Get or create session
        if request.session_id:
            session = SessionService.get_session_by_id(db, request.session_id, user_id)
            if not session:
                yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
                return
            session_id = session.id
        else:
            session = SessionService.create_session(db, user_id)
            session_id = session.id
        
        # Add user message to DB
        SessionService.add_message(
            db, 
            session_id, 
            MessageCreate(content=request.message), 
            "user"
        )
        
        # Build history
        db_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()
        history = [{"role": m.role, "content": m.content} for m in db_messages[:-1]]
        
        # Stream response
        full_response = ""
        async for chunk in self.agent.stream_message(str(request.message), str(session_id), str(user_id), history=history):
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:])
                    if data.get("type") == "token":
                        full_response += data.get("content", "")
                except:
                    pass
            yield chunk
        
        # After stream: Add assistant response to DB
        SessionService.add_message(
            db,
            session_id,
            MessageCreate(content=full_response),
            "assistant"
        )
        
        # Auto-title (same logic)
        db_session = db.query(Session).filter(Session.id == session_id).first()
        if db_session and db_session.title in ("New Chat", None, ""):
            try:
                title = await self.agent.generate_title(request.message)
                if title:
                    db_session.title = title
                    db.commit()
            except Exception as e:
                logger.warning(f"Title gene failed: {e}")