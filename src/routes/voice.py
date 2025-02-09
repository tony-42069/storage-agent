from fastapi import APIRouter, Request, HTTPException, Depends
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
) -> Dict:
    """
    Handle incoming Twilio voice calls
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response
    """
    try:
        # Get request form data
        form_data = await request.form()
        
        # Validate request
        if not twilio.validate_request(dict(form_data)):
            logger.warning("Invalid Twilio request received")
            raise HTTPException(status_code=400, detail="Invalid request")
        
        # Generate initial response
        response = twilio.handle_incoming_call()
        logger.info(f"Handled incoming call from {form_data.get('From')}")
        
        return {"twiml": response}
        
    except Exception as e:
        logger.error(f"Error handling incoming call: {e}", exc_info=True)
        return {"twiml": twilio.handle_error(e)}

@router.post("/process")
async def process_speech(
    request: Request,
    twilio: TwilioService = Depends(get_twilio_service)
) -> Dict:
    """
    Process speech input from Twilio
    
    Args:
        request: FastAPI request object
        twilio: TwilioService instance
        
    Returns:
        TwiML response
    """
    try:
        # Get request form data
        form_data = await request.form()
        
        # Validate request
        if not twilio.validate_request(dict(form_data)):
            logger.warning("Invalid Twilio request received")
            raise HTTPException(status_code=400, detail="Invalid request")
        
        # Get speech result
        speech_result = form_data.get('SpeechResult')
        if not speech_result:
            logger.warning("No speech result in request")
            raise HTTPException(status_code=400, detail="No speech input")
        
        # Process speech and generate response
        response = twilio.process_speech(speech_result)
        logger.info(f"Processed speech input: {speech_result[:100]}...")
        
        return {"twiml": response}
        
    except Exception as e:
        logger.error(f"Error processing speech: {e}", exc_info=True)
        return {"twiml": twilio.handle_error(e)}

@router.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    return {"status": "healthy"}
