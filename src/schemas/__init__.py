"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a user."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr
    role: str = Field(default="operator", pattern="^(admin|operator|viewer)$")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(admin|operator|viewer)$")
    active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    username: str
    email: str
    role: str
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str
    token_type: str
    expires_in: int


class ReservationCreate(BaseModel):
    """Schema for creating a reservation."""
    unit_id: str = Field(..., min_length=1)
    customer_phone: str = Field(..., min_length=10)
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    start_date: datetime
    duration_months: int = Field(..., ge=1, le=24)


class ReservationResponse(BaseModel):
    """Schema for reservation response."""
    id: int
    reservation_id: str
    unit_id: str
    customer_phone: str
    customer_name: Optional[str]
    customer_email: Optional[str]
    start_date: datetime
    duration_months: int
    monthly_price: float
    total_price: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UnitResponse(BaseModel):
    """Schema for unit response."""
    id: int
    unit_id: str
    size: str
    square_feet: int
    floor: int
    price: float
    climate_controlled: bool
    available: bool
    features: List[str]
    
    class Config:
        from_attributes = True


class FacilityResponse(BaseModel):
    """Schema for facility response."""
    id: int
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[str]
    hours: Dict[str, Dict[str, str]]
    amenities: List[str]
    
    class Config:
        from_attributes = True


class ConversationSessionResponse(BaseModel):
    """Schema for conversation session response."""
    session_id: str
    customer_phone: Optional[str]
    current_intent: Optional[str]
    previous_intents: List[str]
    status: str
    start_time: datetime
    last_update: datetime
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    detail: Optional[Dict[str, Any]] = None


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses."""
    error: str = "validation_error"
    message: str
    detail: List[Dict[str, Any]]


class HealthComponentResponse(BaseModel):
    """Schema for health check component."""
    status: str
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    missing: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    components: Dict[str, HealthComponentResponse]
    summary: Dict[str, int]
    latency_ms: int
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Schema for metrics response."""
    app_uptime_seconds: float
    app_requests_total: int
    app_errors_total: int
    app_conversations_total: int
    calls: Dict[str, Any]
    timestamp: datetime
