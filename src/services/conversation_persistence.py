"""Conversation context persistence service."""
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

from src.models.conversation_session import ConversationSession
from src.core.conversation import ConversationContext, Intent, Entity
from src.db.session import get_sync_session, get_async_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationPersistenceService:
    """Service for persisting and retrieving conversation sessions."""
    
    def __init__(self, use_async: bool = False):
        """
        Initialize persistence service.
        
        Args:
            use_async: Use async session operations
        """
        self.use_async = use_async
    
    def _entity_to_dict(self, entity: Entity) -> dict:
        """Convert Entity to dictionary."""
        return {
            'type': entity.type,
            'value': entity.value,
            'confidence': entity.confidence,
        }
    
    def _dict_to_entity(self, data: dict) -> Entity:
        """Convert dictionary to Entity."""
        return Entity(
            type=data.get('type', ''),
            value=data.get('value', ''),
            confidence=data.get('confidence', 1.0),
        )
    
    def save_context(self, context: ConversationContext) -> Optional[ConversationSession]:
        """
        Save conversation context to database.
        
        Args:
            context: ConversationContext to save
            
        Returns:
            Saved ConversationSession or None on error
        """
        session = get_sync_session()
        try:
            existing = session.query(ConversationSession).filter_by(
                session_id=context.session_id
            ).first()
            
            if existing:
                existing.current_intent = context.current_intent.value if context.current_intent else None
                existing.previous_intents = [i.value for i in context.previous_intents]
                existing.entities = {k: self._entity_to_dict(v) for k, v in context.entities.items()}
                existing.user_preferences = context.user_preferences
                existing.last_update = datetime.utcnow()
                
                if context.current_intent == Intent.UNKNOWN:
                    duration = (existing.last_update - existing.start_time).total_seconds()
                    existing.duration_seconds = int(duration)
                
                db_session = existing
            else:
                db_session = ConversationSession(
                    session_id=context.session_id,
                    current_intent=context.current_intent.value if context.current_intent else None,
                    previous_intents=[i.value for i in context.previous_intents],
                    entities={k: self._entity_to_dict(v) for k, v in context.entities.items()},
                    user_preferences=context.user_preferences,
                    status='active',
                    start_time=context.start_time,
                    last_update=context.last_update,
                )
                session.add(db_session)
            
            session.commit()
            logger.info(f"Saved conversation session: {context.session_id}")
            return db_session
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving conversation context: {e}")
            return None
        finally:
            session.close()
    
    def load_context(self, session_id: str) -> Optional[ConversationContext]:
        """
        Load conversation context from database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationContext or None if not found
        """
        session = get_sync_session()
        try:
            db_session = session.query(ConversationSession).filter_by(
                session_id=session_id
            ).first()
            
            if not db_session:
                return None
            
            context = ConversationContext(
                session_id=db_session.session_id,
                start_time=db_session.start_time or datetime.utcnow(),
                last_update=db_session.last_update or datetime.utcnow(),
                turn_count=len(db_session.previous_intents) + (1 if db_session.current_intent else 0),
                current_intent=Intent(db_session.current_intent) if db_session.current_intent else Intent.UNKNOWN,
                previous_intents=[Intent(i) for i in db_session.previous_intents or []],
                entities={k: self._dict_to_entity(v) for k, v in (db_session.entities or {}).items()},
                user_preferences=db_session.user_preferences or {},
            )
            
            logger.info(f"Loaded conversation session: {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error loading conversation context: {e}")
            return None
        finally:
            session.close()
    
    def end_session(self, session_id: str, summary: Optional[str] = None):
        """
        Mark a conversation session as ended.
        
        Args:
            session_id: Session identifier
            summary: Optional session summary
        """
        session = get_sync_session()
        try:
            db_session = session.query(ConversationSession).filter_by(
                session_id=session_id
            ).first()
            
            if db_session:
                db_session.status = 'completed'
                db_session.end_time = datetime.utcnow()
                db_session.summary = summary
                
                if db_session.start_time:
                    duration = (db_session.end_time - db_session.start_time).total_seconds()
                    db_session.duration_seconds = int(duration)
                
                session.commit()
                logger.info(f"Ended conversation session: {session_id}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error ending conversation session: {e}")
        finally:
            session.close()
    
    def get_session_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent conversation sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries
        """
        session = get_sync_session()
        try:
            sessions = session.query(ConversationSession).order_by(
                ConversationSession.start_time.desc()
            ).limit(limit).all()
            
            return [s.to_dict() for s in sessions]
            
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Remove sessions older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta
        session = get_sync_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = session.query(ConversationSession).filter(
                ConversationSession.end_time.isnot(None),
                ConversationSession.end_time < cutoff,
                ConversationSession.status != 'active'
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up {result} old conversation sessions")
            return result
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0
        finally:
            session.close()


conversation_persistence = ConversationPersistenceService()
