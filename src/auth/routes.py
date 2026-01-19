"""Authentication routes for admin users."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.auth.jwt_auth import (
    authenticate_user,
    create_tokens,
    admin_store,
    get_current_active_user,
    TokenData,
    auth_config,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response body."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response body."""
    access_token: str
    token_type: str
    expires_in: int


class UserCreateRequest(BaseModel):
    """User creation request."""
    username: str
    password: str
    email: EmailStr
    role: str = "operator"


class UserResponse(BaseModel):
    """User response."""
    id: int
    username: str
    email: str
    role: str
    active: bool


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT tokens.
    
    Returns access and refresh tokens on successful authentication.
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        logger = __import__('src.auth.jwt_auth', fromlist=['get_logger']).get_logger(__name__)
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = create_tokens(user)
    
    logger = __import__('src.auth.jwt_auth', fromlist=['get_logger']).get_logger(__name__)
    logger.info(f"User logged in: {user.username}")
    
    return LoginResponse(
        **tokens,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Returns a new access token if refresh token is valid.
    """
    from src.auth.jwt_auth import jwt, TokenData
    
    try:
        payload = jwt.decode(
            request.refresh_token,
            auth_config.SECRET_KEY,
            algorithms=[auth_config.ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user = admin_store.get_user(payload.get("username", ""))
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        access_token = auth_config.create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role,
            }
        )
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: TokenData = Depends(get_current_active_user)):
    """Get information about the currently authenticated user."""
    user = admin_store.get_user(current_user.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


@router.get("/users", response_model=list)
async def list_users(current_user: TokenData = Depends(require_role("admin"))):
    """List all admin users (admin only)."""
    return admin_store.list_users()


def require_role(*roles: str):
    """Dependency to require specific roles."""
    async def role_checker(
        current_user: TokenData = Depends(get_current_active_user)
    ) -> TokenData:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker
