import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.services.twilio_service import TwilioService
from src.core.entities import EntityExtractor

client = TestClient(app)


@pytest.fixture
def mock_twilio_service():
    """Fixture to provide a mocked TwilioService"""
    with patch('src.routes.voice.get_twilio_service') as mock:
        service = TwilioService(
            account_sid='test_sid',
            auth_token='test_token',
            phone_number='+1234567890',
            voice_action_url=''
        )
        mock.return_value = service
        yield service


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/voice/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]


def test_entity_extraction():
    """Test entity extraction functionality"""
    extractor = EntityExtractor()
    
    text = "I need a 10x15 storage unit"
    entities = extractor.extract_all(text)
    assert "unit_size" in entities
    assert entities["unit_size"].width == 10
    assert entities["unit_size"].length == 15
    
    text = "I need storage for 6 months"
    entities = extractor.extract_all(text)
    assert "duration" in entities
    assert entities["duration"].amount == 6
    assert entities["duration"].unit == "month"
    
    text = "I want to move in next week"
    entities = extractor.extract_all(text)
    assert "move_in_date" in entities
    assert "next week" in entities["move_in_date"].value


@pytest.mark.asyncio
async def test_conversation_context():
    """Test maintaining conversation context across interactions"""
    pytest.skip("Conversation context feature not implemented yet")
