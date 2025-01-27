from typing import Dict, Optional
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from core.entities import EntityExtractor
from services.storage_service import StorageService
from utils.logger import get_logger

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
        self.client = Client(account_sid, auth_token)
        self.phone_number = phone_number
        self.entity_extractor = EntityExtractor()
        self.storage_service = StorageService(facility_id, facility_api_key)
        
        logger.info("Initialized Twilio service with storage facility integration")

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

    def process_speech(self, speech_result: str) -> str:
        """
        Process speech input and generate appropriate response
        
        Args:
            speech_result: Transcribed speech from Twilio
            
        Returns:
            TwiML response as string
        """
        logger.info(f"Processing speech input: {speech_result}")
        
        # Extract entities from speech
        entities = self.entity_extractor.extract_all(speech_result)
        logger.debug(f"Extracted entities: {entities}")
        
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action='/voice/process',
            language='en-US',
            enhanced='true',
            speech_timeout='auto'
        )
        
        # Generate response based on extracted entities
        if 'unit_size' in entities:
            unit_size = entities['unit_size']
            available_units = self.storage_service.get_available_units(unit_size.value)
            
            if available_units:
                unit = available_units[0]  # Get the first available unit of requested size
                features = ", ".join(unit.features[:2])  # List first 2 features
                gather.say(
                    f'Great! We have a {unit_size.value} unit available for ${unit.price:.2f} per month. '
                    f'This unit features {features}. '
                    'Would you like to reserve it?',
                    voice='Polly.Amy'
                )
            else:
                # Suggest alternative sizes
                all_units = self.storage_service.get_available_units()
                if all_units:
                    sizes = ", ".join(set(u.size for u in all_units[:2]))
                    gather.say(
                        f'I apologize, but we don\'t have any {unit_size.value} units available right now. '
                        f'However, we do have {sizes} units available. '
                        'Would you like to hear about those options?',
                        voice='Polly.Amy'
                    )
                else:
                    gather.say(
                        'I apologize, but we don\'t have any units available at the moment. '
                        'Would you like me to take your contact information for when one becomes available?',
                        voice='Polly.Amy'
                    )
        elif 'duration' in entities:
            duration = entities['duration']
            # Get all available units for price comparison
            available_units = self.storage_service.get_available_units()
            if available_units:
                # Sort by price and get cheapest option
                cheapest = min(available_units, key=lambda u: u.price)
                total_price = cheapest.price * duration.amount
                gather.say(
                    f'For a {duration.value} rental, our prices start at ${cheapest.price:.2f} per month '
                    f'for a {cheapest.size} unit, totaling ${total_price:.2f}. '
                    'What size unit are you interested in?',
                    voice='Polly.Amy'
                )
            else:
                gather.say(
                    'I understand you\'re looking for a {duration.value} rental. '
                    'What size unit are you interested in? For example, a 10 by 10 unit?',
                    voice='Polly.Amy'
                )
        else:
            # Get available sizes for suggestions
            available_units = self.storage_service.get_available_units()
            if available_units:
                sizes = ", ".join(sorted(set(u.size for u in available_units[:3])))
                gather.say(
                    f'We currently have {sizes} units available. '
                    'What size would work best for you?',
                    voice='Polly.Amy'
                )
            else:
                gather.say(
                    'Could you tell me what size storage unit you\'re looking for? '
                    'For example, a 10 by 10 unit?',
                    voice='Polly.Amy'
                )
        
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

    def validate_request(self, request_data: Dict) -> bool:
        """
        Validate incoming Twilio request
        
        Args:
            request_data: Request parameters from Twilio
            
        Returns:
            True if request is valid, False otherwise
        """
        try:
            # Basic validation of required fields
            required_fields = ['CallSid', 'From']
            if not all(field in request_data for field in required_fields):
                logger.warning("Missing required fields in Twilio request")
                return False
            
            # Additional validation could be added here
            # - Validate caller phone number format
            # - Check if caller is in allowed list
            # - Verify request signature
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating Twilio request: {e}")
            return False
