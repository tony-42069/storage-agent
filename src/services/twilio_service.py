"""Twilio service integration module."""
from typing import Dict, Optional

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from core.config import get_settings

settings = get_settings()


class TwilioService:
    """Service class for Twilio integration."""

    def __init__(self):
        """Initialize Twilio client."""
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    def create_voice_response(self) -> VoiceResponse:
        """Create a new TwiML voice response."""
        return VoiceResponse()

    def generate_welcome_twiml(self) -> str:
        """Generate TwiML for welcome message."""
        response = self.create_voice_response()
        response.say(
            "Welcome to Storage Agent. How may I assist you today?",
            voice="Polly.Amy"
        )
        response.pause(length=1)
        return str(response)

    def handle_incoming_call(self, call_data: Dict) -> str:
        """Handle incoming call and generate appropriate TwiML response."""
        response = self.create_voice_response()
        
        # Initial greeting
        response.say(
            "Thank you for calling. I'm here to help you with your storage needs.",
            voice="Polly.Amy"
        )
        
        # Gather customer input
        gather = response.gather(
            input="speech",
            action="/api/voice/process",
            method="POST",
            language="en-US",
            speechTimeout="auto"
        )
        gather.say(
            "Please tell me what you're looking for, "
            "such as unit availability, pricing, or general information.",
            voice="Polly.Amy"
        )
        
        # If no input received
        response.redirect("/api/voice/welcome")
        
        return str(response)

    def process_speech_input(self, speech_result: Optional[str]) -> str:
        """Process speech input and generate appropriate response."""
        response = self.create_voice_response()
        
        if not speech_result:
            response.say(
                "I'm sorry, I didn't catch that. Could you please repeat?",
                voice="Polly.Amy"
            )
            response.redirect("/api/voice/welcome")
            return str(response)
        
        # TODO: Implement NLP processing for speech input
        # For now, return a generic response
        response.say(
            "I understand you're interested in our storage services. "
            "Let me connect you with our virtual assistant for more detailed information.",
            voice="Polly.Amy"
        )
        
        return str(response)
