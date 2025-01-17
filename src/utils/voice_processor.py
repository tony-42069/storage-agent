"""Voice processing utilities."""
from typing import Dict, Optional, Tuple

import speech_recognition as sr
from fastapi import HTTPException


class VoiceProcessor:
    """Utility class for processing voice input."""

    def __init__(self):
        """Initialize voice processor."""
        self.recognizer = sr.Recognizer()

    async def process_speech(self, audio_data: bytes) -> Tuple[str, float]:
        """
        Process speech data and return transcribed text with confidence score.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Tuple of (transcribed_text, confidence_score)
            
        Raises:
            HTTPException: If speech processing fails
        """
        try:
            # Convert audio data to AudioData object
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            
            # Attempt to recognize speech
            result = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=True
            )
            
            if not result:
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand audio"
                )
            
            # Get the most confident result
            best_result = max(result["alternative"], key=lambda x: x.get("confidence", 0))
            
            return (
                best_result["transcript"],
                best_result.get("confidence", 0.0)
            )
            
        except sr.UnknownValueError:
            raise HTTPException(
                status_code=400,
                detail="Speech not understood"
            )
        except sr.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Speech recognition service error: {str(e)}"
            )

    def extract_intent(self, text: str) -> Dict[str, str]:
        """
        Extract intent and entities from transcribed text.
        
        Args:
            text: Transcribed text from speech
            
        Returns:
            Dictionary containing intent and any extracted entities
        """
        # TODO: Implement more sophisticated NLP
        # For now, use simple keyword matching
        text = text.lower()
        
        intents = {
            "availability": ["available", "unit", "space", "storage"],
            "pricing": ["price", "cost", "rate", "much"],
            "information": ["information", "details", "tell me about"],
            "hours": ["hours", "open", "close", "access"],
            "location": ["where", "location", "address", "directions"],
            "payment": ["pay", "payment", "bill", "invoice"]
        }
        
        # Find matching intent
        for intent, keywords in intents.items():
            if any(keyword in text for keyword in keywords):
                return {
                    "intent": intent,
                    "confidence": 0.8,  # Placeholder confidence score
                    "text": text
                }
        
        # Default to general inquiry if no specific intent found
        return {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "text": text
        }

    def validate_audio_quality(self, audio_data: bytes) -> Optional[str]:
        """
        Validate audio quality and return error message if issues found.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Error message if quality issues found, None otherwise
        """
        # TODO: Implement audio quality validation
        # For now, just check if audio data exists
        if not audio_data or len(audio_data) < 1000:
            return "Audio data too short or empty"
        
        return None
