import pytest
from datetime import datetime, timedelta

from services.storage_service import StorageService, StorageUnit, Reservation

@pytest.fixture
def storage_service():
    """Fixture to provide a StorageService instance"""
    return StorageService(
        facility_id="test_facility",
        api_key="test_api_key"
    )

def test_get_available_units(storage_service):
    """Test retrieving available units"""
    # Test all available units
    units = storage_service.get_available_units()
    assert len(units) > 0
    assert all(isinstance(unit, StorageUnit) for unit in units)
    assert all(unit.available for unit in units)
    
    # Test filtering by size
    units = storage_service.get_available_units(size="10x10")
    assert len(units) == 1
    assert units[0].size == "10x10"
    assert units[0].available

def test_get_unit_price(storage_service):
    """Test retrieving unit prices"""
    # Test existing unit
    price = storage_service.get_unit_price("A101")
    assert price == 49.99
    
    # Test non-existent unit
    price = storage_service.get_unit_price("NONEXISTENT")
    assert price is None

def test_create_reservation(storage_service):
    """Test creating unit reservations"""
    # Test successful reservation
    reservation = storage_service.create_reservation(
        unit_id="A101",
        customer_phone="+1234567890",
        start_date=datetime.now() + timedelta(days=1),
        duration_months=3
    )
    assert isinstance(reservation, Reservation)
    assert reservation.unit_id == "A101"
    assert reservation.status == "pending"
    assert reservation.duration_months == 3
    assert reservation.total_price == 49.99 * 3
    
    # Test reservation for unavailable unit
    reservation = storage_service.create_reservation(
        unit_id="C303",  # This unit is marked as unavailable in mock data
        customer_phone="+1234567890",
        start_date=datetime.now() + timedelta(days=1),
        duration_months=3
    )
    assert reservation is None

def test_get_unit_features(storage_service):
    """Test retrieving unit features"""
    # Test existing unit
    features = storage_service.get_unit_features("B202")
    assert len(features) > 0
    assert "Climate Control" in features
    assert "Indoor Access" in features
    
    # Test non-existent unit
    features = storage_service.get_unit_features("NONEXISTENT")
    assert len(features) == 0

def test_check_unit_availability(storage_service):
    """Test checking unit availability"""
    # Test available unit
    assert storage_service.check_unit_availability("A101") is True
    
    # Test unavailable unit
    assert storage_service.check_unit_availability("C303") is False
    
    # Test non-existent unit
    assert storage_service.check_unit_availability("NONEXISTENT") is False

def test_unit_size_variations(storage_service):
    """Test different unit sizes are properly handled"""
    units = storage_service.get_available_units()
    sizes = {unit.size for unit in units}
    assert "5x5" in sizes
    assert "10x10" in sizes
    
    # Verify square footage calculations
    for unit in units:
        if unit.size == "5x5":
            assert unit.square_feet == 25
        elif unit.size == "10x10":
            assert unit.square_feet == 100

def test_climate_controlled_units(storage_service):
    """Test filtering and identifying climate controlled units"""
    units = storage_service.get_available_units()
    climate_controlled = [unit for unit in units if unit.climate_controlled]
    assert len(climate_controlled) > 0
    
    # Verify climate controlled units have appropriate features
    for unit in climate_controlled:
        assert "Climate Control" in unit.features

def test_pricing_tiers(storage_service):
    """Test different pricing tiers based on unit size"""
    units = storage_service.get_available_units()
    
    # Verify larger units cost more
    unit_prices = {unit.size: unit.price for unit in units}
    assert unit_prices["5x5"] < unit_prices["10x10"]  # Smaller units should cost less
