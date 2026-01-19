"""Versioned reservations API routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from src.auth import get_current_active_user, TokenData
from src.services.storage_service import StorageService, Reservation
from src.schemas import ReservationResponse, ReservationCreate
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reservations", tags=["reservations"])

storage_service = StorageService()


@router.get("", response_model=List[ReservationResponse])
async def list_reservations(
    status: Optional[str] = Query(None, description="Filter by status"),
    unit_id: Optional[str] = Query(None, description="Filter by unit ID"),
    limit: int = Query(50, ge=1, le=100),
    current_user: TokenData = Depends(get_current_active_user)
):
    """List reservations (authenticated users)."""
    # In production, this would query the database
    return []


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Get a specific reservation (authenticated users)."""
    # In production, this would query the database
    raise HTTPException(
        status_code=404,
        detail="Reservation not found"
    )


@router.post("", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    request: ReservationCreate,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Create a new reservation (authenticated users)."""
    reservation = storage_service.create_reservation(
        unit_id=request.unit_id,
        customer_phone=request.customer_phone,
        start_date=request.start_date,
        duration_months=request.duration_months,
    )
    
    if not reservation:
        raise HTTPException(
            status_code=400,
            detail="Unable to create reservation. Unit may not be available."
        )
    
    return {
        "id": 0,
        "reservation_id": reservation.reservation_id,
        "unit_id": reservation.unit_id,
        "customer_phone": reservation.customer_phone,
        "customer_name": None,
        "customer_email": None,
        "start_date": reservation.start_date,
        "duration_months": reservation.duration_months,
        "monthly_price": reservation.total_price / reservation.duration_months,
        "total_price": reservation.total_price,
        "status": reservation.status,
        "created_at": datetime.utcnow(),
    }


@router.post("/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Cancel a reservation (authenticated users)."""
    # In production, this would update the database
    return {"message": f"Reservation {reservation_id} cancelled"}


@router.post("/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Confirm a reservation (admin only)."""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Operator or admin access required"
        )
    
    # In production, this would update the database
    return {"message": f"Reservation {reservation_id} confirmed"}
