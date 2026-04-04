from sqlalchemy.orm import Session
from app.services.session_service import SessionService
from app.core.agent import ChatAgent
from app.schemas.chat import ChatRequest, ChatResponse, MessageCreate
from uuid import UUID
import asyncio

class ChatService:
    def __init__(self):
        self.agent = ChatAgent()
    
    async def process_message(self, db: Session, user_id: UUID, request: ChatRequest) -> ChatResponse:
        # Get or create session
        if request.session_id:
            session = SessionService.get_session_by_id(db, request.session_id, user_id)
            if not session:
                raise ValueError("Session not found")
            session_id = session.id
        else:
            session = SessionService.create_session(db, user_id)
            session_id = session.id
        
        # Add user message
        SessionService.add_message(
            db, 
            session_id, 
            MessageCreate(content=request.message), 
            "user"
        )
        
        # Process with agent
        agent_result = await self.agent.process_message(
            str(request.message),
            str(session_id),
            str(user_id)
        )
        
        # Add assistant response
        SessionService.add_message(
            db,
            session_id,
            MessageCreate(content=agent_result["response"]),
            "assistant"
        )
        
        return ChatResponse(
            message=agent_result["response"],
            session_id=session_id,
            route_type=agent_result["route_type"]
        )