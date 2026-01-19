"""Facility API client for storage management system integration."""
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
import asyncio
import aiohttp
from urllib.parse import urljoin

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FacilityUnit:
    """Represents a storage unit from the facility API."""
    unit_id: str
    size: str
    square_feet: int
    price: float
    floor: int
    climate_controlled: bool
    available: bool
    features: List[str]


@dataclass
class FacilityInfo:
    """Represents facility information."""
    facility_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    hours: Dict[str, Dict[str, str]]


class FacilityApiError(Exception):
    """Custom exception for facility API errors."""
    pass


class FacilityApiClient:
    """Async HTTP client for facility management system API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize facility API client.
        
        Args:
            base_url: Base URL for facility API
            api_key: API authentication key
            api_secret: API authentication secret
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = base_url or os.getenv('FACILITY_API_URL', '')
        self.api_key = api_key or os.getenv('FACILITY_API_KEY', '')
        self.api_secret = api_secret or os.getenv('FACILITY_API_SECRET', '')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"Initialized FacilityApiClient with base_url: {self.base_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to facility API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            FacilityApiError: If request fails after retries
        """
        session = await self._get_session()
        url = urljoin(self.base_url, endpoint)
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method, url, json=data, params=params, headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        raise FacilityApiError("Invalid API credentials")
                    elif response.status == 404:
                        raise FacilityApiError(f"Endpoint not found: {endpoint}")
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}")
        
        raise FacilityApiError(f"Request failed after {self.max_retries} attempts: {last_error}")
    
    async def get_units(
        self,
        size: Optional[str] = None,
        available_only: bool = True
    ) -> List[FacilityUnit]:
        """
        Get storage units from facility API.
        
        Args:
            size: Optional size filter (e.g., "10x10")
            available_only: Only return available units
            
        Returns:
            List of FacilityUnit objects
        """
        params = {}
        if size:
            params['size'] = size
        if available_only:
            params['available'] = 'true'
        
        try:
            data = await self._request('GET', '/api/v1/units', params=params)
            units = []
            for unit_data in data.get('units', []):
                units.append(FacilityUnit(
                    unit_id=unit_data['unit_id'],
                    size=unit_data['size'],
                    square_feet=unit_data['square_feet'],
                    price=unit_data['price'],
                    floor=unit_data['floor'],
                    climate_controlled=unit_data.get('climate_controlled', False),
                    available=unit_data['available'],
                    features=unit_data.get('features', [])
                ))
            
            logger.info(f"Retrieved {len(units)} units from API")
            return units
            
        except FacilityApiError:
            raise
        except Exception as e:
            logger.error(f"Error fetching units: {e}")
            raise FacilityApiError(f"Failed to fetch units: {e}")
    
    async def get_unit(self, unit_id: str) -> Optional[FacilityUnit]:
        """
        Get a specific storage unit by ID.
        
        Args:
            unit_id: Unit identifier
            
        Returns:
            FacilityUnit or None if not found
        """
        try:
            data = await self._request('GET', f'/api/v1/units/{unit_id}')
            return FacilityUnit(
                unit_id=data['unit_id'],
                size=data['size'],
                square_feet=data['square_feet'],
                price=data['price'],
                floor=data['floor'],
                climate_controlled=data.get('climate_controlled', False),
                available=data['available'],
                features=data.get('features', [])
            )
        except FacilityApiError as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def get_unit_price(self, unit_id: str) -> Optional[float]:
        """
        Get price for a specific unit.
        
        Args:
            unit_id: Unit identifier
            
        Returns:
            Price or None if unit not found
        """
        unit = await self.get_unit(unit_id)
        return unit.price if unit else None
    
    async def check_availability(self, unit_id: str) -> bool:
        """
        Check if a unit is available.
        
        Args:
            unit_id: Unit identifier
            
        Returns:
            True if available, False otherwise
        """
        unit = await self.get_unit(unit_id)
        return unit.available if unit else False
    
    async def create_reservation(
        self,
        unit_id: str,
        customer_phone: str,
        start_date: str,
        duration_months: int
    ) -> Dict[str, Any]:
        """
        Create a unit reservation.
        
        Args:
            unit_id: Unit to reserve
            customer_phone: Customer phone number
            start_date: Move-in date (ISO format)
            duration_months: Rental duration
            
        Returns:
            Reservation details from API
        """
        data = {
            'unit_id': unit_id,
            'customer_phone': customer_phone,
            'start_date': start_date,
            'duration_months': duration_months
        }
        
        response = await self._request('POST', '/api/v1/reservations', data=data)
        logger.info(f"Created reservation for unit {unit_id}")
        return response
    
    async def get_facility_info(self) -> Optional[FacilityInfo]:
        """
        Get facility information.
        
        Returns:
            FacilityInfo or None if not available
        """
        try:
            data = await self._request('GET', '/api/v1/facility')
            return FacilityInfo(
                facility_id=data['facility_id'],
                name=data['name'],
                address=data['address'],
                city=data['city'],
                state=data['state'],
                zip_code=data['zip_code'],
                phone=data['phone'],
                hours=data.get('hours', {})
            )
        except FacilityApiError:
            return None


class MockFacilityApiClient(FacilityApiClient):
    """Mock client for development and testing."""
    
    def __init__(self):
        """Initialize mock client with sample data."""
        super().__init__()
        self._mock_units = [
            FacilityUnit(
                unit_id="A101",
                size="5x5",
                square_feet=25,
                price=49.99,
                floor=1,
                climate_controlled=False,
                available=True,
                features=["Ground Floor", "Drive Up"]
            ),
            FacilityUnit(
                unit_id="B202",
                size="10x10",
                square_feet=100,
                price=149.99,
                floor=2,
                climate_controlled=True,
                available=True,
                features=["Climate Control", "Indoor Access"]
            ),
            FacilityUnit(
                unit_id="C303",
                size="10x15",
                square_feet=150,
                price=199.99,
                floor=3,
                climate_controlled=True,
                available=False,
                features=["Climate Control", "Indoor Access", "Large Door"]
            ),
        ]
    
    async def get_units(
        self,
        size: Optional[str] = None,
        available_only: bool = True
    ) -> List[FacilityUnit]:
        """Return mock units with optional filtering."""
        units = [
            unit for unit in self._mock_units
            if (not available_only or unit.available) and
               (not size or unit.size == size)
        ]
        logger.debug(f"Mock: returned {len(units)} units")
        return units
    
    async def get_unit(self, unit_id: str) -> Optional[FacilityUnit]:
        """Return mock unit by ID."""
        for unit in self._mock_units:
            if unit.unit_id == unit_id:
                return unit
        return None
    
    async def get_unit_price(self, unit_id: str) -> Optional[float]:
        """Return mock unit price."""
        unit = await self.get_unit(unit_id)
        return unit.price if unit else None
    
    async def check_availability(self, unit_id: str) -> bool:
        """Check mock unit availability."""
        unit = await self.get_unit(unit_id)
        return unit.available if unit else False
    
    async def create_reservation(
        self,
        unit_id: str,
        customer_phone: str,
        start_date: str,
        duration_months: int
    ) -> Dict[str, Any]:
        """Create mock reservation."""
        return {
            'reservation_id': f"R{start_date.replace('-', '')}",
            'unit_id': unit_id,
            'status': 'pending',
            'total_price': (await self.get_unit_price(unit_id) or 0) * duration_months
        }
    
    async def get_facility_info(self) -> FacilityInfo:
        """Return mock facility info."""
        return FacilityInfo(
            facility_id="default",
            name="Mock Storage Facility",
            address="123 Storage Lane",
            city="Storage City",
            state="SC",
            zip_code="12345",
            phone="+1555123456",
            hours={
                "monday": {"open": "09:00", "close": "18:00"},
                "tuesday": {"open": "09:00", "close": "18:00"},
                "wednesday": {"open": "09:00", "close": "18:00"},
                "thursday": {"open": "09:00", "close": "18:00"},
                "friday": {"open": "09:00", "close": "18:00"},
                "saturday": {"open": "09:00", "close": "17:00"},
                "sunday": {"open": "closed", "close": "closed"},
            }
        )
