from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from src.models.base import Base

class ReservationStatus(enum.Enum):
    """Possible states for a reservation"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Reservation(Base):
    """Storage unit reservation model"""
    __tablename__ = 'reservations'

    id = Column(Integer, primary_key=True)
    reservation_id = Column(String, unique=True, nullable=False)  # e.g., "R20250126123456"
    
    # Customer information
    customer_name = Column(String)
    customer_phone = Column(String, nullable=False)
    customer_email = Column(String)
    
    # Reservation details
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)  # Null for indefinite rentals
    duration_months = Column(Integer, nullable=False)
    monthly_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING)
    
    # Payment information
    payment_method = Column(String)
    payment_status = Column(String)
    deposit_amount = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    unit_id = Column(Integer, ForeignKey('units.id'), nullable=False)
    unit = relationship("Unit", back_populates="reservations")
    
    facility_id = Column(Integer, ForeignKey('facilities.id'), nullable=False)
    facility = relationship("Facility", back_populates="reservations")

    def __repr__(self):
        return (f"<Reservation(id='{self.reservation_id}', "
                f"unit='{self.unit.unit_id if self.unit else None}', "
                f"status={self.status.value})>")

    def calculate_total_price(self) -> float:
        """Calculate total price for the reservation period"""
        return self.monthly_price * self.duration_months

    def confirm(self):
        """Confirm the reservation"""
        if self.status == ReservationStatus.PENDING:
            self.status = ReservationStatus.CONFIRMED
            if self.unit:
                self.unit.available = False

    def cancel(self):
        """Cancel the reservation"""
        if self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
            self.status = ReservationStatus.CANCELLED
            if self.unit:
                self.unit.available = True

    def complete(self):
        """Mark the reservation as completed"""
        if self.status == ReservationStatus.CONFIRMED:
            self.status = ReservationStatus.COMPLETED
            if self.unit:
                self.unit.available = True

    @property
    def is_active(self) -> bool:
        """Check if reservation is currently active"""
        if self.status != ReservationStatus.CONFIRMED:
            return False
            
        now = datetime.utcnow()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date <= now
