import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from services.twilio_service import TwilioService
from core.entities import EntityExtractor

client = TestClient(app)

@pytest.fixture
def mock_twilio_service():
    """Fixture to provide a mocked TwilioService"""
    with patch('routes.voice.get_twilio_service') as mock:
        service = TwilioService(
            account_sid='test_sid',
            auth_token='test_token',
            phone_number='+1234567890'
        )
        mock.return_value = service
        yield service

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/voice/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_incoming_call_flow(mock_twilio_service):
    """Test the complete incoming call flow"""
    # Test initial call handling
    response = client.post("/voice/incoming", data={
        "CallSid": "test_call_sid",
        "From": "+1234567890"
    })
    assert response.status_code == 200
    assert "Welcome to Storage Agent" in response.json()["twiml"]
    assert "How can I help you" in response.json()["twiml"]

def test_speech_processing_with_unit_size(mock_twilio_service):
    """Test speech processing with unit size mention"""
    response = client.post("/voice/process", data={
        "CallSid": "test_call_sid",
        "From": "+1234567890",
        "SpeechResult": "I need a 10 by 10 storage unit"
    })
    assert response.status_code == 200
    twiml = response.json()["twiml"]
    assert "10x10" in twiml
    assert "availability and pricing" in twiml

def test_speech_processing_with_duration(mock_twilio_service):
    """Test speech processing with duration mention"""
    response = client.post("/voice/process", data={
        "CallSid": "test_call_sid",
        "From": "+1234567890",
        "SpeechResult": "I need storage for 3 months"
    })
    assert response.status_code == 200
    twiml = response.json()["twiml"]
    assert "3 months" in twiml
    assert "size" in twiml.lower()

def test_entity_extraction():
    """Test entity extraction functionality"""
    extractor = EntityExtractor()
    
    # Test unit size extraction
    text = "I need a 10x15 storage unit"
    entities = extractor.extract_all(text)
    assert "unit_size" in entities
    assert entities["unit_size"].width == 10
    assert entities["unit_size"].length == 15
    
    # Test duration extraction
    text = "I need storage for 6 months"
    entities = extractor.extract_all(text)
    assert "duration" in entities
    assert entities["duration"].amount == 6
    assert entities["duration"].unit == "month"
    
    # Test move-in date extraction
    text = "I want to move in next week"
    entities = extractor.extract_all(text)
    assert "move_in_date" in entities
    assert "next week" in entities["move_in_date"].value

def test_error_handling(mock_twilio_service):
    """Test error handling in voice endpoints"""
    # Test missing required fields
    response = client.post("/voice/incoming", data={})
    assert response.status_code == 200  # Still returns 200 with error TwiML
    assert "trouble" in response.json()["twiml"].lower()
    
    # Test invalid speech input
    response = client.post("/voice/process", data={
        "CallSid": "test_call_sid",
        "From": "+1234567890"
    })
    assert response.status_code == 400
    assert "No speech input" in response.json()["detail"]

@pytest.mark.asyncio
async def test_conversation_context():
    """Test maintaining conversation context across interactions"""
    # This would test the conversation engine's ability to maintain context
    # across multiple interactions, but we need to implement this feature first
    pytest.skip("Conversation context feature not implemented yet")
