"""Conversation engine for managing dialog flows and context."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class Intent(str, Enum):
    """Supported conversation intents."""
    
    AVAILABILITY = "availability"
    PRICING = "pricing"
    INFORMATION = "information"
    HOURS = "hours"
    LOCATION = "location"
    PAYMENT = "payment"
    GENERAL = "general_inquiry"
    UNKNOWN = "unknown"


class Entity(BaseModel):
    """Named entity extracted from conversation."""
    
    type: str
    value: str
    confidence: float


@dataclass
class ConversationContext:
    """Maintains context for a conversation session."""
    
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    turn_count: int = 0
    current_intent: Intent = Intent.UNKNOWN
    previous_intents: List[Intent] = field(default_factory=list)
    entities: Dict[str, Entity] = field(default_factory=dict)
    user_preferences: Dict[str, str] = field(default_factory=dict)
    
    def update_intent(self, intent: Intent):
        """Update current intent and track history."""
        if self.current_intent != Intent.UNKNOWN:
            self.previous_intents.append(self.current_intent)
        self.current_intent = intent
        self.last_update = datetime.now()
        self.turn_count += 1
    
    def add_entity(self, entity: Entity):
        """Add or update an entity in the context."""
        self.entities[entity.type] = entity
        self.last_update = datetime.now()
    
    def set_preference(self, key: str, value: str):
        """Set a user preference."""
        self.user_preferences[key] = value
        self.last_update = datetime.now()


class ConversationEngine:
    """Core conversation management engine."""
    
    def __init__(self):
        """Initialize conversation engine."""
        self.active_contexts: Dict[str, ConversationContext] = {}
    
    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get existing context or create new one."""
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = ConversationContext(session_id=session_id)
        return self.active_contexts[session_id]
    
    def process_intent(
        self,
        session_id: str,
        intent: Intent,
        confidence: float,
        entities: Optional[List[Entity]] = None
    ) -> str:
        """
        Process an intent and generate appropriate response.
        
        Args:
            session_id: Unique session identifier
            intent: Detected intent
            confidence: Intent confidence score
            entities: Optional list of extracted entities
            
        Returns:
            Response text for the intent
        """
        context = self.get_or_create_context(session_id)
        context.update_intent(intent)
        
        if entities:
            for entity in entities:
                context.add_entity(entity)
        
        # Generate response based on intent and context
        if intent == Intent.AVAILABILITY:
            return self._handle_availability(context)
        elif intent == Intent.PRICING:
            return self._handle_pricing(context)
        elif intent == Intent.INFORMATION:
            return self._handle_information(context)
        elif intent == Intent.HOURS:
            return self._handle_hours(context)
        elif intent == Intent.LOCATION:
            return self._handle_location(context)
        elif intent == Intent.PAYMENT:
            return self._handle_payment(context)
        else:
            return self._handle_general(context)
    
    def _handle_availability(self, context: ConversationContext) -> str:
        """Handle availability intent."""
        # TODO: Integrate with actual inventory system
        return (
            "We have several unit sizes available. "
            "Our most popular sizes are 5x5, 5x10, and 10x10. "
            "Would you like to know more about a specific size?"
        )
    
    def _handle_pricing(self, context: ConversationContext) -> str:
        """Handle pricing intent."""
        # TODO: Integrate with pricing engine
        return (
            "Our units start at $49 per month for a 5x5, "
            "$89 for a 5x10, and $149 for a 10x10. "
            "Would you like me to check availability for any of these sizes?"
        )
    
    def _handle_information(self, context: ConversationContext) -> str:
        """Handle information intent."""
        return (
            "We offer climate-controlled storage units with 24/7 access, "
            "state-of-the-art security, and flexible lease terms. "
            "What specific information would you like to know more about?"
        )
    
    def _handle_hours(self, context: ConversationContext) -> str:
        """Handle hours intent."""
        return (
            "Our office is open Monday through Friday from 9 AM to 6 PM, "
            "and Saturday from 9 AM to 5 PM. However, tenants have 24/7 access "
            "to their units using their secure entry code."
        )
    
    def _handle_location(self, context: ConversationContext) -> str:
        """Handle location intent."""
        # TODO: Integrate with facility information
        return (
            "We're conveniently located at 123 Storage Lane. "
            "Would you like directions or would you prefer me to text them to you?"
        )
    
    def _handle_payment(self, context: ConversationContext) -> str:
        """Handle payment intent."""
        return (
            "We accept all major credit cards, and you can pay online, "
            "in person, or set up automatic payments. "
            "Would you like information about any specific payment method?"
        )
    
    def _handle_general(self, context: ConversationContext) -> str:
        """Handle general inquiries."""
        return (
            "I can help you with unit availability, pricing, facility information, "
            "hours, location, or payment options. What would you like to know more about?"
        )
