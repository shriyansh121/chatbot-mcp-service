from sqlalchemy.orm import Session as DBSession
from app.services.session_service import SessionService
from app.core.agent import ChatAgent
from app.schemas.chat import ChatRequest, MessageCreate
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

    async def process_message_stream(
        self, db: DBSession, user_id: UUID, request: ChatRequest
    ) -> AsyncGenerator[str, None]:
        """Stream a response. The frontend ALWAYS sends a session_id now."""

        # ── Get or create session ───────────────────────────────────
        if request.session_id:
            session = SessionService.get_session_by_id(db, request.session_id, user_id)
            if not session:
                yield f"data: {json.dumps({'type': 'token', 'content': '⚠️ Session not found.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            session_id = session.id
        else:
            # Fallback: create session if frontend didn't send one
            session = SessionService.create_session(db, user_id)
            session_id = session.id

        # ── Save user message to DB ─────────────────────────────────
        SessionService.add_message(db, session_id, MessageCreate(content=request.message), "user")

        # ── Build conversation history (last 10 messages for context) ──
        db_messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        # Exclude the message we just added (the last one) from history
        history = [{"role": m.role, "content": m.content} for m in db_messages[:-1]]
        # Limit to last 10 messages to keep context window manageable
        history = history[-10:]

        # ── Stream from agent ───────────────────────────────────────
        full_response = ""
        async for chunk in self.agent.stream_message(
            user_message=request.message,
            session_id=str(session_id),
            user_id=str(user_id),
            history=history,
        ):
            # Collect response text for DB persistence
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk[6:].strip())
                    if data.get("type") == "token":
                        full_response += data.get("content", "")
                except Exception:
                    pass

            yield chunk

        # ── Save assistant response to DB ───────────────────────────
        if full_response.strip():
            SessionService.add_message(
                db, session_id, MessageCreate(content=full_response), "assistant"
            )

        # ── Auto-generate title on first message ────────────────────
        db_session = db.query(Session).filter(Session.id == session_id).first()
        if db_session and db_session.title in ("New Chat", None, ""):
            try:
                title = await self.agent.generate_title(request.message)
                if title:
                    db_session.title = title
                    db.commit()
            except Exception as e:
                logger.warning(f"Title generation failed: {e}")