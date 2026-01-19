from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from src.models.base import Base


class ConversationSession(Base):
    """Stores conversation session data for persistence."""
    __tablename__ = 'conversation_sessions'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    
    customer_phone = Column(String(20))
    customer_name = Column(String(100))
    
    current_intent = Column(String(50))
    previous_intents = Column(JSON, default=list)
    
    entities = Column(JSON, default=dict)
    user_preferences = Column(JSON, default=dict)
    
    transcript = Column(Text)
    summary = Column(Text)
    
    status = Column(String(20), default='active')
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    duration_seconds = Column(Integer)
    
    reservation_id = Column(Integer, ForeignKey('reservations.id'), nullable=True)
    reservation = relationship("Reservation")

    def __repr__(self):
        return f"<ConversationSession(session_id='{self.session_id}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'customer_phone': self.customer_phone,
            'current_intent': self.current_intent,
            'previous_intents': self.previous_intents,
            'entities': self.entities,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
        }
