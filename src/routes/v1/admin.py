"""Versioned admin API routes."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr

from src.auth import (
    authenticate_user,
    create_tokens,
    admin_store,
    get_current_active_user,
    TokenData,
    auth_config,
)
from src.schemas import UserResponse, UserCreate, LoginRequest, LoginResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list)
async def list_users(current_user: TokenData = Depends(get_current_active_user)):
    """List all admin users (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return admin_store.list_users()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Create a new admin user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        user = admin_store.create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            role=request.role,
        )
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "active": True,
            "created_at": user.created_at,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{username}")
async def deactivate_user(
    username: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Deactivate a user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user = admin_store.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Mark user as inactive (would update database in production)
    return {"message": f"User {username} deactivated"}


@router.get("/stats")
async def get_admin_stats(current_user: TokenData = Depends(get_current_active_user)):
    """Get admin statistics (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {
        "total_users": len(admin_store.list_users()),
        "active_users": len([u for u in admin_store.list_users() if u["active"]]),
    }
