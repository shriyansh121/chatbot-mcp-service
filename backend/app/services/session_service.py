from sqlalchemy.orm import Session
from app.db.models.session_table import Session
from app.db.models.message import Message
from app.schemas.chat import SessionCreate, MessageCreate
from typing import List, Optional
from uuid import UUID

class SessionService:
    
    @staticmethod
    def create_session(db: Session, user_id: UUID, session_data: SessionCreate = None) -> Session:
        db_session = Session(
            user_id=user_id,
            title=session_data.title if session_data else "New Chat"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session
    
    @staticmethod
    def get_user_sessions(db: Session, user_id: UUID, archived: bool = False) -> List[Session]:
        return db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_archived == archived
        ).order_by(Session.updated_at.desc()).all()
    
    @staticmethod
    def get_session_by_id(db: Session, session_id: UUID, user_id: UUID) -> Optional[Session]:
        return db.query(Session).filter(
            Session.id == session_id,
            Session.user_id == user_id
        ).first()
    
    @staticmethod
    def archive_session(db: Session, session_id: UUID, user_id: UUID) -> bool:
        db_session = SessionService.get_session_by_id(db, session_id, user_id)
        if db_session:
            db_session.is_archived = True
            db.commit()
            return True
        return False
    
    @staticmethod
    def delete_session(db: Session, session_id: UUID, user_id: UUID) -> bool:
        db_session = SessionService.get_session_by_id(db, session_id, user_id)
        if db_session:
            db.delete(db_session)
            db.commit()
            return True
        return False
    
    @staticmethod
    def add_message(db: Session, session_id: UUID, message_data: MessageCreate, role: str = "user") -> Message:
        db_message = Message(
            session_id=session_id,
            role=role,
            content=message_data.content
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        # Update session updated_at
        db_session = db.query(Session).filter(Session.id == session_id).first()
        if db_session:
            db_session.updated_at = db_message.created_at
            db.commit()
        
        return db_message
    
    @staticmethod
    def get_session_messages(db: Session, session_id: UUID, user_id: UUID) -> List[Message]:
        # Verify session belongs to user
        session = SessionService.get_session_by_id(db, session_id, user_id)
        if not session:
            return []
        
        return db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc()).all()