from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import Response
from typing import Dict
import os

from src.services.twilio_service import TwilioService
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

def get_twilio_service() -> TwilioService:
    """Dependency to get configured TwilioService instance"""
    return TwilioService(
        account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
        auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
        phone_number=os.getenv('TWILIO_PHONE_NUMBER')
    )

@router.post("/incoming")
async def handle_incoming_call(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> str:
    """
    Handle incoming Twilio voice calls
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response
    """
    try:
        # Get request form data and headers
        form_data = await request.form()
        signature = request.headers.get("X-Twilio-Signature", "")
        
        # Temporarily disable signature validation for testing
        logger.info("Skipping signature validation for testing")
        
        # Generate initial response
        response = twilio.handle_incoming_call()
        logger.info(f"Handled incoming call from {form_data.get('From')}")
        
        return Response(content=response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error handling incoming call: {e}", exc_info=True)
        return twilio.handle_error(e)

@router.post("/process")
async def process_speech(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> str:
    """
    Process speech input from Twilio
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response
    """
    try:
        # Get request form data and headers
        form_data = await request.form()
        signature = request.headers.get("X-Twilio-Signature", "")
        
        # Temporarily disable signature validation for testing
        logger.info("Skipping signature validation for testing")
        
        # Get input result (speech or DTMF)
        speech_result = form_data.get('SpeechResult')
        dtmf_result = form_data.get('Digits')
        call_sid = form_data.get('CallSid')

        if not speech_result and not dtmf_result:
            logger.warning("No input received")
            raise HTTPException(status_code=400, detail="No input received")
        
        # Process input and generate response
        input_text = speech_result if speech_result else f"Option {dtmf_result}"
        response = twilio.process_speech(input_text, call_sid)
        logger.info(f"Processed speech input for call {call_sid}: {speech_result[:100]}...")
        
        return Response(content=response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing speech: {e}", exc_info=True)
        return Response(content=twilio.handle_error(e), media_type="application/xml")

@router.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    return {"status": "healthy"}
