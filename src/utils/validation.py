"""Request validation utilities and custom validators."""
import re
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException
from pydantic import BaseModel, Field, validator, EmailStr
from pydantic.types import constr


def validate_phone_number(phone: str) -> str:
    """Validate and normalize phone number."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check for valid US phone number
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) == 11:
        return f"+{digits[:1]} {digits[1:4]} {digits[4:7]}-{digits[7:]}"
    elif len(digits) == 12:
        return f"+{digits[:2]} {digits[2:5]} {digits[5:8]}-{digits[8:]}"
    
    raise ValueError("Invalid phone number format")


def validate_unit_size(size: str) -> str:
    """Validate storage unit size format."""
    pattern = r'^\d+\s*[xX]\s*\d+$'
    if not re.match(pattern, size):
        raise ValueError("Invalid unit size format. Expected: WxL (e.g., '10x10')")
    
    parts = re.split(r'[xX]', size)
    width = int(parts[0].strip())
    length = int(parts[1].strip())
    
    if width <= 0 or length <= 0:
        raise ValueError("Unit dimensions must be positive")
    
    if width > 100 or length > 100:
        raise ValueError("Unit dimensions exceed maximum size")
    
    return f"{width}x{length}"


def validate_date_future(date_str: str) -> str:
    """Validate that a date is in the future."""
    from datetime import datetime
    
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
    ]
    
    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    
    if parsed is None:
        raise ValueError("Invalid date format")
    
    if parsed < datetime.utcnow():
        raise ValueError("Date must be in the future")
    
    return date_str


def validate_duration_months(duration: int) -> int:
    """Validate rental duration."""
    if duration < 1:
        raise ValueError("Duration must be at least 1 month")
    if duration > 24:
        raise ValueError("Maximum duration is 24 months")
    return duration


class ValidatedLoginRequest(BaseModel):
    """Validated login request."""
    username: constr(min_length=3, max_length=50) = Field(..., description="Username")
    password: constr(min_length=8) = Field(..., description="Password")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric with underscores')
        return v.lower()


class ValidatedReservationCreate(BaseModel):
    """Validated reservation creation request."""
    unit_id: str = Field(..., min_length=1, max_length=20, description="Unit identifier")
    customer_phone: str = Field(..., min_length=10, max_length=20, description="Customer phone number")
    customer_name: Optional[str] = Field(None, max_length=100, description="Customer name")
    customer_email: Optional[EmailStr] = Field(None, description="Customer email")
    start_date: str = Field(..., description="Move-in date (YYYY-MM-DD)")
    duration_months: int = Field(..., ge=1, le=24, description="Rental duration in months")
    
    @validator('unit_id')
    def validate_unit_id(cls, v):
        if not re.match(r'^[A-Z0-9]+$', v):
            raise ValueError('Unit ID must be alphanumeric uppercase')
        return v
    
    @validator('customer_phone')
    def validate_phone(cls, v):
        return validate_phone_number(v)
    
    @validator('start_date')
    def validate_start_date(cls, v):
        return validate_date_future(v)
    
    @validator('duration_months')
    def validate_duration(cls, v):
        return validate_duration_months(v)


class ValidatedUserCreate(BaseModel):
    """Validated user creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr
    role: str = Field(default="operator", pattern="^(admin|operator|viewer)$")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric with underscores')
        return v.lower()
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


async def validate_request_body(request: Request) -> Dict[str, Any]:
    """Validate request body and return parsed data."""
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            return {"valid": True, "data": body, "errors": []}
        except Exception as e:
            return {"valid": False, "data": None, "errors": [str(e)]}
    
    return {"valid": True, "data": {}, "errors": []}


def create_validation_error_response(errors: List[str]) -> Dict[str, Any]:
    """Create a standardized validation error response."""
    return {
        "error": "validation_error",
        "message": "Request validation failed",
        "detail": {"errors": errors}
    }


class AuditLogEntry(BaseModel):
    """Schema for audit log entries."""
    timestamp: str
    user_id: Optional[str]
    username: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    method: str
    path: str
    status_code: int
    duration_ms: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_body: Optional[Dict[str, Any]]
    response_body: Optional[Dict[str, Any]]
    error: Optional[str]
