"""Voice processing utilities."""
import re
from typing import Dict, List, Optional, Tuple

import speech_recognition as sr
from fastapi import HTTPException

from core.conversation import ConversationEngine, Entity, Intent


class VoiceProcessor:
    """Utility class for processing voice input."""

    def __init__(self):
        """Initialize voice processor."""
        self.recognizer = sr.Recognizer()
        self.conversation_engine = ConversationEngine()
        
        # Intent keyword mappings
        self.intent_keywords = {
            Intent.AVAILABILITY: ["available", "unit", "space", "storage"],
            Intent.PRICING: ["price", "cost", "rate", "much"],
            Intent.INFORMATION: ["information", "details", "tell me about"],
            Intent.HOURS: ["hours", "open", "close", "access"],
            Intent.LOCATION: ["where", "location", "address", "directions"],
            Intent.PAYMENT: ["pay", "payment", "bill", "invoice"]
        }
        
        # Entity type patterns
        self.entity_patterns = {
            "unit_size": [
                r"(\d+)\s*x\s*(\d+)",  # e.g., "10x10"
                r"(\d+)\s*by\s*(\d+)",  # e.g., "10 by 10"
            ],
            "date": [
                r"(today|tomorrow|next week)",
                r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            ],
            "duration": [
                r"(\d+)\s*(month|year|week)",
                r"(short|long)\s*term",
            ]
        }
        self.compiled_patterns = {
            entity_type: [re.compile(pattern, re.IGNORECASE) 
                         for pattern in patterns]
            for entity_type, patterns in self.entity_patterns.items()
        }

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

    def extract_intent_and_entities(
        self,
        text: str,
        session_id: str
    ) -> Tuple[Intent, float, List[Entity]]:
        """
        Extract intent and entities from transcribed text.
        
        Args:
            text: Transcribed text from speech
            session_id: Session identifier for context
            
        Returns:
            Tuple of (intent, confidence_score, entities)
        """
        text = text.lower()
        entities = []
        max_confidence = 0.0
        detected_intent = Intent.UNKNOWN
        
        # Find matching intent based on keywords
        for intent, keywords in self.intent_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                confidence = min(0.5 + (matches * 0.1), 0.9)  # Scale confidence with matches
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_intent = intent
        
        # Extract entities using patterns
        # TODO: Implement more sophisticated entity extraction
        # For now, just demonstrate the structure
        if "5x5" in text or "five by five" in text:
            entities.append(Entity(
                type="unit_size",
                value="5x5",
                confidence=0.9
            ))
        elif "10x10" in text or "ten by ten" in text:
            entities.append(Entity(
                type="unit_size",
                value="10x10",
                confidence=0.9
            ))
        
        # Get response from conversation engine
        response = self.conversation_engine.process_intent(
            session_id=session_id,
            intent=detected_intent,
            confidence=max_confidence,
            entities=entities
        )
        
        return detected_intent, max_confidence, entities, response

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
