"""Voice processing utilities."""
import re
from typing import Dict, List, Optional, Tuple

import speech_recognition as sr
from fastapi import HTTPException

from core.conversation import ConversationEngine, Entity, Intent
from utils.logger import logger


class VoiceProcessor:
    """Utility class for processing voice input."""

    def __init__(self):
        """Initialize voice processor."""
        logger.info("Initializing VoiceProcessor")
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
        logger.debug("VoiceProcessor initialized with patterns", extra={
            "intent_keywords": self.intent_keywords,
            "entity_patterns": self.entity_patterns
        })

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
            logger.info("Processing speech data", extra={"data_size": len(audio_data)})
            
            # Convert audio data to AudioData object
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            
            # Attempt to recognize speech
            result = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=True
            )
            
            if not result:
                logger.warning("No speech recognition result")
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand audio"
                )
            
            # Get the most confident result
            best_result = max(result["alternative"], key=lambda x: x.get("confidence", 0))
            
            logger.info("Speech processed successfully", extra={
                "transcript": best_result["transcript"],
                "confidence": best_result.get("confidence", 0.0)
            })
            
            return (
                best_result["transcript"],
                best_result.get("confidence", 0.0)
            )
            
        except sr.UnknownValueError:
            logger.error("Speech not understood")
            raise HTTPException(
                status_code=400,
                detail="Speech not understood"
            )
        except sr.RequestError as e:
            logger.error("Speech recognition service error", extra={"error": str(e)})
            raise HTTPException(
                status_code=500,
                detail=f"Speech recognition service error: {str(e)}"
            )

    def extract_intent_and_entities(
        self,
        text: str,
        session_id: str
    ) -> Tuple[Intent, float, List[Entity], str]:
        """
        Extract intent and entities from transcribed text.
        
        Args:
            text: Transcribed text from speech
            session_id: Session identifier for context
            
        Returns:
            Tuple of (intent, confidence_score, entities, response)
        """
        logger.info("Extracting intent and entities", extra={
            "text": text,
            "session_id": session_id
        })
        
        text = text.lower()
        entities = []
        max_confidence = 0.0
        detected_intent = Intent.UNKNOWN
        
        # Find matching intent based on keywords
        for intent, keywords in self.intent_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                confidence = min(0.5 + (matches * 0.1), 0.9)
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_intent = intent
        
        logger.debug("Intent detection result", extra={
            "detected_intent": detected_intent,
            "confidence": max_confidence
        })
        
        # Extract entities using patterns
        for entity_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    entity_value = match.group(0)
                    entities.append(Entity(
                        type=entity_type,
                        value=entity_value,
                        confidence=0.9
                    ))
                    logger.debug("Entity extracted", extra={
                        "type": entity_type,
                        "value": entity_value
                    })
        
        # Get response from conversation engine
        response = self.conversation_engine.process_intent(
            session_id=session_id,
            intent=detected_intent,
            confidence=max_confidence,
            entities=entities
        )
        
        logger.info("Intent processing complete", extra={
            "intent": detected_intent,
            "confidence": max_confidence,
            "entity_count": len(entities)
        })
        
        return detected_intent, max_confidence, entities, response

    def validate_audio_quality(self, audio_data: bytes) -> Optional[str]:
        """
        Validate audio quality and return error message if issues found.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Error message if quality issues found, None otherwise
        """
        logger.debug("Validating audio quality", extra={"data_size": len(audio_data)})
        
        if not audio_data or len(audio_data) < 1000:
            logger.warning("Audio data too short or empty")
            return "Audio data too short or empty"
        
        return None
