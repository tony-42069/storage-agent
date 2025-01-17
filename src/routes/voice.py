"""Voice processing routes."""
from typing import Dict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import PlainTextResponse

from services.twilio_service import TwilioService
from utils.voice_processor import VoiceProcessor

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Dependencies
def get_twilio_service() -> TwilioService:
    """Dependency for TwilioService."""
    return TwilioService()

def get_voice_processor() -> VoiceProcessor:
    """Dependency for VoiceProcessor."""
    return VoiceProcessor()

@router.post("/welcome", response_class=PlainTextResponse)
async def welcome_handler(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> str:
    """
    Handle initial incoming calls.
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response as string
    """
    return twilio.generate_welcome_twiml()

@router.post("/incoming", response_class=PlainTextResponse)
async def incoming_call_handler(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> str:
    """
    Handle incoming Twilio voice calls.
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response as string
    """
    # Extract call data from request
    form_data = await request.form()
    call_data = dict(form_data)
    
    return twilio.handle_incoming_call(call_data)

@router.post("/process", response_class=PlainTextResponse)
async def process_speech_handler(
    request: Request,
    SpeechResult: str = Form(None),
    twilio: TwilioService = Depends(get_twilio_service),
    processor: VoiceProcessor = Depends(get_voice_processor)
) -> str:
    """
    Process speech input from Twilio.
    
    Args:
        request: FastAPI request object
        SpeechResult: Transcribed speech from Twilio
        twilio: TwilioService instance
        processor: VoiceProcessor instance
        
    Returns:
        TwiML response as string
    """
    if SpeechResult:
        # Extract intent from speech
        intent_data = processor.extract_intent(SpeechResult)
        
        # TODO: Use intent data to generate more specific responses
        # For now, pass through to basic speech processing
        return twilio.process_speech_input(SpeechResult)
    
    return twilio.process_speech_input(None)

@router.post("/fallback", response_class=PlainTextResponse)
async def fallback_handler(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> str:
    """
    Handle fallback for failed calls or errors.
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response as string
    """
    response = twilio.create_voice_response()
    response.say(
        "I apologize, but we're experiencing technical difficulties. "
        "Please try your call again in a few moments.",
        voice="Polly.Amy"
    )
    return str(response)
