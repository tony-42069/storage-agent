import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger('storage_agent.entities')

@dataclass
class Entity:
    """Base class for extracted entities"""
    value: str
    confidence: float = 1.0

@dataclass
class UnitSize:
    """Storage unit size entity"""
    width: int
    length: int
    value: str
    confidence: float = 1.0
    
    @property
    def square_feet(self) -> int:
        return self.width * self.length

@dataclass
class Duration:
    """Duration entity"""
    amount: int
    unit: str  # 'month', 'week', 'year'
    value: str
    confidence: float = 1.0

class EntityExtractor:
    """Extract structured entities from natural language text"""
    
    # Common patterns
    UNIT_SIZE_PATTERNS = [
        r'(\d+)\s*(?:x|by|\*)\s*(\d+)',  # e.g., "10x10" or "10 by 10"
        r'(\d+)\s*(?:ft|foot|feet)\s*(?:x|by|\*)\s*(\d+)',  # e.g., "10 feet by 10"
        r'(\d+)\s*(?:ft|foot|feet)\s*square',  # e.g., "100 square feet"
    ]
    
    DURATION_PATTERNS = [
        r'(?:for\s+)?(\d+)\s+(month|week|year)s?',  # e.g., "for 3 months"
        r'(\d+)(?:-|\s+)(month|week|year)',  # e.g., "6-month" or "6 month"
    ]
    
    MOVE_IN_PATTERNS = [
        r'move\s+in\s+(today|tomorrow|next\s+week|next\s+month)',
        r'move\s+in\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))',
        r'starting\s+(today|tomorrow|next\s+week|next\s+month)',
    ]

    def extract_unit_size(self, text: str) -> Optional[UnitSize]:
        """Extract storage unit dimensions from text"""
        text = text.lower()
        
        for pattern in self.UNIT_SIZE_PATTERNS:
            if match := re.search(pattern, text):
                try:
                    # Handle different formats
                    if len(match.groups()) == 2:
                        width, length = map(int, match.groups())
                    else:
                        # Square footage format
                        sq_ft = int(match.group(1))
                        width = length = int(sq_ft ** 0.5)  # Assume square unit
                        
                    logger.debug(f"Extracted unit size: {width}x{length}")
                    return UnitSize(
                        value=f"{width}x{length}",
                        width=width,
                        length=length
                    )
                except ValueError as e:
                    logger.warning(f"Failed to parse unit size: {e}")
                    continue
        
        return None

    def extract_duration(self, text: str) -> Optional[Duration]:
        """Extract rental duration from text"""
        text = text.lower()
        
        for pattern in self.DURATION_PATTERNS:
            if match := re.search(pattern, text):
                amount = int(match.group(1))
                unit = match.group(2)
                logger.debug(f"Extracted duration: {amount} {unit}(s)")
                return Duration(
                    value=f"{amount} {unit}{'s' if amount > 1 else ''}",
                    amount=amount,
                    unit=unit
                )
        
        return None

    def extract_move_in_date(self, text: str) -> Optional[Entity]:
        """Extract desired move-in date from text"""
        text = text.lower()
        
        for pattern in self.MOVE_IN_PATTERNS:
            if match := re.search(pattern, text):
                date_str = match.group(1)
                logger.debug(f"Extracted move-in date: {date_str}")
                return Entity(value=date_str)
        
        return None

    def extract_all(self, text: str) -> Dict[str, Entity]:
        """Extract all possible entities from text"""
        entities = {}
        
        if unit_size := self.extract_unit_size(text):
            entities['unit_size'] = unit_size
            
        if duration := self.extract_duration(text):
            entities['duration'] = duration
            
        if move_in := self.extract_move_in_date(text):
            entities['move_in_date'] = move_in
            
        logger.info(f"Extracted entities: {entities}")
        return entities
