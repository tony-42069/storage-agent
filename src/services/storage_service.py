from typing import Dict, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class StorageUnit:
    """Represents a storage unit"""
    unit_id: str
    size: str  # e.g., "10x10"
    square_feet: int
    price: float
    floor: int
    climate_controlled: bool
    available: bool
    features: List[str]

@dataclass
class Reservation:
    """Represents a unit reservation"""
    reservation_id: str
    unit_id: str
    customer_phone: str
    start_date: datetime
    duration_months: int
    status: str  # 'pending', 'confirmed', 'cancelled'
    total_price: float

class StorageService:
    """Interface for storage facility management system"""
    
    def __init__(self, facility_id: str, api_key: str):
        """
        Initialize storage service
        
        Args:
            facility_id: ID of the storage facility
            api_key: API key for facility management system
        """
        self.facility_id = facility_id
        self.api_key = api_key
        logger.info(f"Initialized storage service for facility {facility_id}")
        
        # TODO: Replace with actual API integration
        # This is temporary mock data for development
        self._mock_units = {
            "A101": StorageUnit(
                unit_id="A101",
                size="5x5",
                square_feet=25,
                price=49.99,
                floor=1,
                climate_controlled=False,
                available=True,
                features=["Ground Floor", "Drive Up"]
            ),
            "B202": StorageUnit(
                unit_id="B202",
                size="10x10",
                square_feet=100,
                price=149.99,
                floor=2,
                climate_controlled=True,
                available=True,
                features=["Climate Control", "Indoor Access"]
            ),
            "C303": StorageUnit(
                unit_id="C303",
                size="10x15",
                square_feet=150,
                price=199.99,
                floor=3,
                climate_controlled=True,
                available=False,
                features=["Climate Control", "Indoor Access", "Large Door"]
            )
        }

    def get_available_units(self, size: Optional[str] = None) -> List[StorageUnit]:
        """
        Get list of available storage units
        
        Args:
            size: Optional size filter (e.g., "10x10")
            
        Returns:
            List of available StorageUnit objects
        """
        try:
            # TODO: Replace with actual API call
            units = [
                unit for unit in self._mock_units.values()
                if unit.available and (not size or unit.size == size)
            ]
            
            logger.info(f"Found {len(units)} available units" + 
                       (f" of size {size}" if size else ""))
            return units
            
        except Exception as e:
            logger.error(f"Error getting available units: {e}")
            return []

    def get_unit_price(self, unit_id: str) -> Optional[float]:
        """
        Get current price for a specific unit
        
        Args:
            unit_id: ID of the storage unit
            
        Returns:
            Current price or None if unit not found
        """
        try:
            # TODO: Replace with actual API call
            if unit := self._mock_units.get(unit_id):
                logger.info(f"Retrieved price for unit {unit_id}: ${unit.price}")
                return unit.price
            return None
            
        except Exception as e:
            logger.error(f"Error getting unit price: {e}")
            return None

    def create_reservation(
        self,
        unit_id: str,
        customer_phone: str,
        start_date: datetime,
        duration_months: int
    ) -> Optional[Reservation]:
        """
        Create a new unit reservation
        
        Args:
            unit_id: ID of the storage unit
            customer_phone: Customer's phone number
            start_date: Desired move-in date
            duration_months: Duration of rental in months
            
        Returns:
            New Reservation object or None if creation failed
        """
        try:
            # TODO: Replace with actual API call
            if unit := self._mock_units.get(unit_id):
                if not unit.available:
                    logger.warning(f"Unit {unit_id} is not available")
                    return None
                    
                reservation = Reservation(
                    reservation_id=f"R{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    unit_id=unit_id,
                    customer_phone=customer_phone,
                    start_date=start_date,
                    duration_months=duration_months,
                    status="pending",
                    total_price=unit.price * duration_months
                )
                
                logger.info(f"Created reservation {reservation.reservation_id} "
                          f"for unit {unit_id}")
                return reservation
                
            logger.warning(f"Unit {unit_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"Error creating reservation: {e}")
            return None

    def get_unit_features(self, unit_id: str) -> List[str]:
        """
        Get features of a specific unit
        
        Args:
            unit_id: ID of the storage unit
            
        Returns:
            List of feature strings
        """
        try:
            # TODO: Replace with actual API call
            if unit := self._mock_units.get(unit_id):
                logger.info(f"Retrieved features for unit {unit_id}")
                return unit.features
            return []
            
        except Exception as e:
            logger.error(f"Error getting unit features: {e}")
            return []

    def check_unit_availability(self, unit_id: str) -> bool:
        """
        Check if a specific unit is available
        
        Args:
            unit_id: ID of the storage unit
            
        Returns:
            True if unit is available, False otherwise
        """
        try:
            # TODO: Replace with actual API call
            if unit := self._mock_units.get(unit_id):
                logger.info(f"Checked availability for unit {unit_id}: {unit.available}")
                return unit.available
            return False
            
        except Exception as e:
            logger.error(f"Error checking unit availability: {e}")
            return False
