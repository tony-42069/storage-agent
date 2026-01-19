"""Versioned units API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from src.auth import get_current_active_user, TokenData
from src.services.storage_service import StorageService
from src.schemas import UnitResponse

router = APIRouter(prefix="/units", tags=["units"])

storage_service = StorageService()


@router.get("", response_model=List[UnitResponse])
async def list_units(
    size: Optional[str] = Query(None, description="Filter by size (e.g., '10x10')"),
    climate_controlled: Optional[bool] = Query(None, description="Filter by climate control"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum monthly price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum monthly price"),
    available_only: bool = Query(True, description="Only show available units"),
    current_user: TokenData = Depends(get_current_active_user)
):
    """List storage units with optional filters (authenticated users)."""
    units = storage_service.get_available_units(size=size)
    
    if climate_controlled is not None:
        units = [u for u in units if u.climate_controlled == climate_controlled]
    
    if min_price is not None:
        units = [u for u in units if u.price >= min_price]
    
    if max_price is not None:
        units = [u for u in units if u.price <= max_price]
    
    if not available_only:
        # In production, fetch all units from database
        pass
    
    return [
        {
            "id": 0,
            "unit_id": u.unit_id,
            "size": u.size,
            "square_feet": u.square_feet,
            "floor": u.floor,
            "price": u.price,
            "climate_controlled": u.climate_controlled,
            "available": u.available,
            "features": u.features,
        }
        for u in units
    ]


@router.get("/{unit_id}", response_model=UnitResponse)
async def get_unit(
    unit_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Get a specific unit (authenticated users)."""
    units = storage_service.get_available_units()
    
    for unit in units:
        if unit.unit_id == unit_id:
            return {
                "id": 0,
                "unit_id": unit.unit_id,
                "size": unit.size,
                "square_feet": unit.square_feet,
                "floor": unit.floor,
                "price": unit.price,
                "climate_controlled": unit.climate_controlled,
                "available": unit.available,
                "features": unit.features,
            }
    
    raise HTTPException(
        status_code=404,
        detail="Unit not found"
    )


@router.get("/{unit_id}/price")
async def get_unit_price(
    unit_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Get the current price for a specific unit (authenticated users)."""
    price = storage_service.get_unit_price(unit_id)
    
    if price is None:
        raise HTTPException(
            status_code=404,
            detail="Unit not found"
        )
    
    return {
        "unit_id": unit_id,
        "price": price,
        "currency": "USD",
        "period": "monthly",
    }


@router.get("/{unit_id}/availability")
async def check_unit_availability(
    unit_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Check if a specific unit is available (authenticated users)."""
    available = storage_service.check_unit_availability(unit_id)
    
    return {
        "unit_id": unit_id,
        "available": available,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/{unit_id}/features")
async def get_unit_features(
    unit_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Get features for a specific unit (authenticated users)."""
    features = storage_service.get_unit_features(unit_id)
    
    if not features:
        raise HTTPException(
            status_code=404,
            detail="Unit not found"
        )
    
    return {
        "unit_id": unit_id,
        "features": features,
    }
