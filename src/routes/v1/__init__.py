"""Versioned API routes (v1)."""
from fastapi import APIRouter

from src.routes.v1 import admin, reservations, units

router = APIRouter(prefix="/v1", tags=["v1"])

router.include_router(admin.router)
router.include_router(reservations.router)
router.include_router(units.router)
