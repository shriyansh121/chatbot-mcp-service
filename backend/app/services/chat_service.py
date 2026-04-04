from sqlalchemy.orm import Session as DBSession
from app.services.session_service import SessionService
from app.core.agent import ChatAgent
from app.schemas.chat import ChatRequest, ChatResponse, MessageCreate
from app.db.models.session_table import Session
from app.db.models.message import Message
from uuid import UUID
import asyncio
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.agent = ChatAgent()
    
    async def process_message(self, db: DBSession, user_id: UUID, request: ChatRequest) -> ChatResponse:
        # Get or create session
        if request.session_id:
            session = SessionService.get_session_by_id(db, request.session_id, user_id)
            if not session:
                raise ValueError("Session not found")
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
        
        # ── Fetch conversation history from messages table ──────
        db_messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc()).all()
        
        # Build history list: [(role, content), ...]
        # Exclude the current user message (last one) — agent receives it separately
        history = []
        for m in db_messages[:-1]:  # All except the latest user msg we just added
            history.append({"role": m.role, "content": m.content})
        
        # Process with agent — now with history context
        agent_result = await self.agent.process_message(
            str(request.message),
            str(session_id),
            str(user_id),
            history=history,
        )
        
        # Add assistant response
        SessionService.add_message(
            db,
            session_id,
            MessageCreate(content=agent_result["response"]),
            "assistant"
        )
        
        # Auto-generate session title if it's still the default "New Chat"
        db_session = db.query(Session).filter(Session.id == session_id).first()
        if db_session and db_session.title in ("New Chat", None, ""):
            try:
                generated_title = await self.agent.generate_title(request.message)
                if generated_title:
                    db_session.title = generated_title
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to auto-generate title: {e}")
        
        return ChatResponse(
            message=agent_result["response"],
            session_id=session_id,
            route_type=agent_result["route_type"]
        )