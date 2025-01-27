from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY

from src.models.base import Base

class Unit(Base):
    """Storage unit model"""
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True)
    unit_id = Column(String, unique=True, nullable=False)  # e.g., "A101"
    size = Column(String, nullable=False)  # e.g., "10x10"
    square_feet = Column(Integer, nullable=False)
    floor = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    climate_controlled = Column(Boolean, default=False)
    available = Column(Boolean, default=True)
    features = Column(ARRAY(String))
    
    # Relationships
    facility_id = Column(Integer, ForeignKey('facilities.id'), nullable=False)
    facility = relationship("Facility", back_populates="units")
    reservations = relationship("Reservation", back_populates="unit")

    def __repr__(self):
        return f"<Unit(unit_id='{self.unit_id}', size='{self.size}', available={self.available})>"

    @property
    def dimensions(self) -> tuple:
        """Get unit dimensions as (width, length)"""
        try:
            width, length = self.size.lower().split('x')
            return (int(width), int(length))
        except (ValueError, AttributeError):
            return (0, 0)

    @property
    def width(self) -> int:
        """Get unit width"""
        return self.dimensions[0]

    @property
    def length(self) -> int:
        """Get unit length"""
        return self.dimensions[1]
