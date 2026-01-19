"""Authentication module with JWT support."""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from src.utils.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


@dataclass
class AdminUser:
    """Represents an admin user."""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime


class TokenData(BaseModel):
    """JWT token payload."""
    sub: str
    username: str
    role: str
    exp: datetime


class AuthConfig:
    """Authentication configuration."""
    
    def __init__(self):
        self.SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.SECRET_KEY,
            algorithm=self.ALGORITHM
        )
        
        return encoded_jwt
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.SECRET_KEY,
            algorithm=self.ALGORITHM
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.SECRET_KEY,
                algorithms=[self.ALGORITHM]
            )
            
            if payload.get("type") != "access":
                return None
            
            return TokenData(
                sub=payload.get("sub", ""),
                username=payload.get("username", ""),
                role=payload.get("role", ""),
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None


auth_config = AuthConfig()


class AdminStore:
    """In-memory admin user storage (use database in production)."""
    
    def __init__(self):
        self._admins: Dict[str, Dict[str, Any]] = {
            "admin": {
                "id": 1,
                "username": "admin",
                "email": "admin@storageagent.com",
                "password_hash": self._hash_password("admin123"),
                "role": "admin",
                "active": True,
                "created_at": datetime.utcnow(),
            },
            "operator": {
                "id": 2,
                "username": "operator",
                "email": "operator@storageagent.com",
                "password_hash": self._hash_password("operator123"),
                "role": "operator",
                "active": True,
                "created_at": datetime.utcnow(),
            },
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = auth_config.SECRET_KEY[:16]
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify a password for a user."""
        if username not in self._admins:
            return False
        
        admin = self._admins[username]
        if not admin.get("active", True):
            return False
        
        return self._hash_password(password) == admin["password_hash"]
    
    def get_user(self, username: str) -> Optional[AdminUser]:
        """Get an admin user by username."""
        if username not in self._admins:
            return None
        
        admin = self._admins[username]
        return AdminUser(
            id=admin["id"],
            username=admin["username"],
            email=admin["email"],
            role=admin["role"],
            created_at=admin["created_at"]
        )
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        role: str = "operator"
    ) -> AdminUser:
        """Create a new admin user."""
        if username in self._admins:
            raise ValueError(f"User {username} already exists")
        
        admin_id = max(a["id"] for a in self._admins.values()) + 1
        
        self._admins[username] = {
            "id": admin_id,
            "username": username,
            "email": email,
            "password_hash": self._hash_password(password),
            "role": role,
            "active": True,
            "created_at": datetime.utcnow(),
        }
        
        logger.info(f"Created new admin user: {username}")
        return self.get_user(username)
    
    def list_users(self) -> list:
        """List all admin users."""
        return [
            {
                "id": v["id"],
                "username": v["username"],
                "email": v["email"],
                "role": v["role"],
                "active": v["active"],
            }
            for v in self._admins.values()
        ]


admin_store = AdminStore()


def authenticate_user(username: str, password: str) -> Optional[AdminUser]:
    """Authenticate a user with username and password."""
    if admin_store.verify_password(username, password):
        return admin_store.get_user(username)
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = auth_config.verify_token(credentials.credentials)
    
    if token_data is None:
        raise credentials_exception
    
    return token_data


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Get current active user (with role verification)."""
    user = admin_store.get_user(current_user.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user


def require_role(*allowed_roles: str):
    """Dependency factory to require specific roles."""
    async def role_checker(
        current_user: TokenData = Depends(get_current_active_user)
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker


def create_tokens(user: AdminUser) -> Dict[str, str]:
    """Create access and refresh tokens for a user."""
    access_token = auth_config.create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
    )
    
    refresh_token = auth_config.create_refresh_token(
        data={
            "sub": str(user.id),
            "username": user.username,
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": auth_config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
