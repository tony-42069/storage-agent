from typing import Dict, List, Optional
from datetime import datetime
import logging
import os
import asyncio
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.services.facility_api_client import (
    FacilityApiClient,
    MockFacilityApiClient,
    FacilityApiError
)

logger = get_logger(__name__)


@dataclass
class StorageUnit:
    """Represents a storage unit"""
    unit_id: str
    size: str
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
    status: str
    total_price: float


class StorageService:
    """Interface for storage facility management system"""
    
    def __init__(
        self,
        facility_id: str = "default",
        api_key: str = "default",
        use_mock: bool = False
    ):
        """
        Initialize storage service
        
        Args:
            facility_id: ID of the storage facility
            api_key: API key for facility management system
            use_mock: Use mock client instead of real API
        """
        self.facility_id = facility_id
        self.api_key = api_key
        self._use_mock = use_mock or os.getenv('USE_MOCK_STORAGE_API', 'false').lower() == 'true'
        
        if self._use_mock:
            self._client: FacilityApiClient = MockFacilityApiClient()
            logger.info(f"Initialized storage service with mock client for facility {facility_id}")
        else:
            self._client = FacilityApiClient()
            logger.info(f"Initialized storage service for facility {facility_id}")
        
        self._sync_client = self._client
    
    def _ensure_sync(self):
        """Ensure synchronous access to the async client."""
        pass
    
    def get_available_units(self, size: Optional[str] = None) -> List[StorageUnit]:
        """
        Get list of available storage units
        
        Args:
            size: Optional size filter (e.g., "10x10")
            
        Returns:
            List of available StorageUnit objects
        """
        try:
            units = asyncio.run(
                self._sync_client.get_units(size=size, available_only=True)
            )
            result = [
                StorageUnit(
                    unit_id=u.unit_id,
                    size=u.size,
                    square_feet=u.square_feet,
                    price=u.price,
                    floor=u.floor,
                    climate_controlled=u.climate_controlled,
                    available=u.available,
                    features=u.features
                )
                for u in units
            ]
            
            logger.info(f"Found {len(result)} available units" + 
                       (f" of size {size}" if size else ""))
            return result
            
        except FacilityApiError as e:
            logger.error(f"API error getting available units: {e}")
            return []
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
            price = asyncio.run(self._sync_client.get_unit_price(unit_id))
            if price is not None:
                logger.info(f"Retrieved price for unit {unit_id}: ${price}")
            return price
            
        except FacilityApiError as e:
            logger.error(f"API error getting unit price: {e}")
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
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            result = asyncio.run(
                self._sync_client.create_reservation(
                    unit_id=unit_id,
                    customer_phone=customer_phone,
                    start_date=start_date_str,
                    duration_months=duration_months
                )
            )
            
            if result:
                reservation = Reservation(
                    reservation_id=result.get('reservation_id', f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                    unit_id=unit_id,
                    customer_phone=customer_phone,
                    start_date=start_date,
                    duration_months=duration_months,
                    status=result.get('status', 'pending'),
                    total_price=result.get('total_price', 0.0)
                )
                
                logger.info(f"Created reservation {reservation.reservation_id} "
                          f"for unit {unit_id}")
                return reservation
            
            return None
            
        except FacilityApiError as e:
            logger.error(f"API error creating reservation: {e}")
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
            unit = asyncio.run(self._sync_client.get_unit(unit_id))
            if unit:
                logger.info(f"Retrieved features for unit {unit_id}")
                return unit.features
            return []
            
        except FacilityApiError as e:
            logger.error(f"API error getting unit features: {e}")
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
            available = asyncio.run(self._sync_client.check_availability(unit_id))
            logger.info(f"Checked availability for unit {unit_id}: {available}")
            return available
            
        except FacilityApiError as e:
            logger.error(f"API error checking availability: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking unit availability: {e}")
            return False
