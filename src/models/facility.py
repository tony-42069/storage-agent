from sqlalchemy import Column, Integer, String, Float, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base

class Facility(Base):
    """Storage facility model"""
    __tablename__ = 'facilities'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String)
    
    # Operating hours stored as JSON
    # Format: {"monday": {"open": "09:00", "close": "18:00"}, ...}
    hours = Column(JSON, nullable=False)
    
    # Facility features (e.g., "24/7 Access", "Security Cameras")
    amenities = Column(JSON, default=list)
    
    # Location coordinates for mapping
    latitude = Column(Float)
    longitude = Column(Float)
    
    # API credentials for facility management system
    api_key = Column(String)
    api_secret = Column(String)
    
    # Relationships
    units = relationship("Unit", back_populates="facility")
    reservations = relationship("Reservation", back_populates="facility")

    def __repr__(self):
        return f"<Facility(name='{self.name}', city='{self.city}')>"

    def get_available_units(self, size: str = None) -> list:
        """Get list of available units, optionally filtered by size"""
        query = [unit for unit in self.units if unit.available]
        if size:
            query = [unit for unit in query if unit.size == size]
        return query

    def get_unit_by_id(self, unit_id: str):
        """Get unit by its identifier (e.g., 'A101')"""
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit
        return None

    def is_open(self, datetime_obj) -> bool:
        """Check if facility is open at given datetime"""
        try:
            day = datetime_obj.strftime('%A').lower()
            if day not in self.hours:
                return False
            
            time_str = datetime_obj.strftime('%H:%M')
            return self.hours[day]['open'] <= time_str <= self.hours[day]['close']
            
        except (KeyError, AttributeError):
            return False
