from typing import Dict, Optional
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.core.entities import EntityExtractor
from src.services.storage_service import StorageService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TwilioService:
    """Handle Twilio voice interactions and call processing"""
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        phone_number: str,
        facility_id: str = "default",
        facility_api_key: str = "default"
    ):
        """
        Initialize Twilio service with credentials
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            phone_number: Twilio phone number to use for calls
            facility_id: ID of the storage facility
            facility_api_key: API key for facility management system
        """
        from src.core.conversation import ConversationEngine, Intent
        
        self.client = Client(account_sid, auth_token)
        self.phone_number = phone_number
        self.auth_token = auth_token
        self.entity_extractor = EntityExtractor()
        self.storage_service = StorageService(facility_id, facility_api_key)
        self.conversation_engine = ConversationEngine()
        self.Intent = Intent  # Make Intent enum available for use
        
        logger.info("Initialized Twilio service with conversation engine")

    def handle_incoming_call(self) -> str:
        """
        Handle initial incoming call and gather user input
        
        Returns:
            TwiML response as string
        """
        response = VoiceResponse()
        
        # Gather speech input
        gather = Gather(
            input='speech',
            action='/voice/process',
            language='en-US',
            enhanced='true',
            speech_timeout='auto'
        )
        
        # Initial greeting
        gather.say(
            'Welcome to Storage Agent. How can I help you find the perfect storage unit today?',
            voice='Polly.Amy'
        )
        
        response.append(gather)
        
        # If no input received
        response.say(
            'I didn\'t catch that. Please call back when you\'re ready.',
            voice='Polly.Amy'
        )
        
        logger.info("Generated initial call response")
        return str(response)

    def process_speech(self, speech_result: str, call_sid: str = None) -> str:
        """
        Process speech input and generate appropriate response
        
        Args:
            speech_result: Transcribed speech from Twilio
            call_sid: Unique identifier for the call session
            
        Returns:
            TwiML response as string
        """
        logger.info(f"Processing speech input: {speech_result}")
        
        # Get or create conversation context
        context = self.conversation_engine.get_or_create_context(call_sid or "default")
        
        # Extract entities from speech
        entities = self.entity_extractor.extract_all(speech_result)
        logger.debug(f"Extracted entities: {entities}")
        
        # Determine intent based on entities
        intent = self.Intent.UNKNOWN
        if 'unit_size' in entities:
            intent = self.Intent.AVAILABILITY
        elif 'duration' in entities:
            intent = self.Intent.PRICING
            
        # Get response from conversation engine
        response_text = self.conversation_engine.process_intent(
            context.session_id,
            intent,
            confidence=1.0,
            entities=[e for e in entities.values()]
        )
        
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action='/voice/process',
            language='en-US',
            enhanced='true',
            speech_timeout='auto'
        )
        
        # Use conversation engine's response
        gather.say(response_text, voice='Polly.Amy')
        
        response.append(gather)
        
        # Fallback if no input received
        response.say(
            'I didn\'t catch that. Please call back when you\'re ready.',
            voice='Polly.Amy'
        )
        
        return str(response)

    def handle_error(self, error: Exception) -> str:
        """
        Generate error response for the user
        
        Args:
            error: Exception that occurred
            
        Returns:
            TwiML response as string
        """
        logger.error(f"Error in call processing: {str(error)}", exc_info=True)
        
        response = VoiceResponse()
        response.say(
            'I apologize, but I\'m having trouble processing your request. '
            'Please try again in a moment.',
            voice='Polly.Amy'
        )
        
        return str(response)

    def validate_request(self, request_data: Dict, request_url: str, signature: str) -> bool:
        """
        Validate incoming Twilio request using request signature
        
        Args:
            request_data: Request parameters from Twilio
            request_url: Full URL of the request
            signature: X-Twilio-Signature header value
            
        Returns:
            True if request is valid, False otherwise
        """
        try:
            from twilio.request_validator import RequestValidator
            
            # Basic validation of required fields
            required_fields = ['CallSid', 'From']
            if not all(field in request_data for field in required_fields):
                logger.warning("Missing required fields in Twilio request")
                return False
            
            # Validate request signature
            validator = RequestValidator(self.auth_token)
            is_valid = validator.validate(
                request_url,
                request_data,
                signature
            )
            
            if not is_valid:
                logger.warning("Invalid Twilio request signature")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating Twilio request: {e}")
            return False
