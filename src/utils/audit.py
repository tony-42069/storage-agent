"""Audit logging middleware and utilities."""
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.utils.logger import get_logger
from src.utils.validation import AuditLogEntry

logger = get_logger(__name__)


class AuditLogger:
    """Audit logging service."""
    
    def __init__(self, enabled: bool = True, max_body_size: int = 1000):
        """
        Initialize audit logger.
        
        Args:
            enabled: Whether audit logging is enabled
            max_body_size: Maximum size of request/response body to log
        """
        self._enabled = enabled
        self._max_body_size = max_body_size
        self._sensitive_fields = {
            'password', 'token', 'secret', 'api_key', 'auth_token',
            'credit_card', 'card_number', 'cvv', 'ssn'
        }
    
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from data."""
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(s in key_lower for s in self._sensitive_fields):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._sanitize(value)
            else:
                result[key] = value
        
        return result
    
    def _truncate(self, data: Any, max_size: int) -> Any:
        """Truncate data to maximum size."""
        if data is None:
            return None
        
        if isinstance(data, str):
            return data[:max_size] + ("..." if len(data) > max_size else "")
        
        if isinstance(data, dict):
            truncated = {}
            current_size = 0
            for key, value in data.items():
                item_size = len(str(value)) if not isinstance(value, str) else len(value)
                if current_size + item_size < max_size:
                    truncated[key] = value
                    current_size += item_size
                else:
                    truncated[key] = str(value)[:max_size - current_size] + "..."
                    break
            return truncated
        
        return str(data)[:max_size]
    
    def log(
        self,
        request: Request,
        response: Response,
        duration_ms: int,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log an API request."""
        if not self._enabled:
            return
        
        try:
            # Get request body
            request_body = {}
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    request_body = self._sanitize(self._truncate(body, self._max_body_size))
                except:
                    pass
            
            # Get response body (for JSON responses)
            response_body = {}
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = json.loads(response.body.decode() if isinstance(response.body, bytes) else response.body)
                    response_body = self._sanitize(self._truncate(body, self._max_body_size))
                except:
                    pass
            
            entry = AuditLogEntry(
                timestamp=datetime.utcnow().isoformat(),
                user_id=user_id,
                username=username,
                action=f"{request.method} {request.url.path}",
                resource=request.url.path.split("/")[-1] or request.url.path,
                resource_id=request.path_params.get("id"),
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_body=request_body,
                response_body=response_body,
                error=error,
            )
            
            logger.info("API request audit", extra={"audit": entry.dict()})
            
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")


audit_logger = AuditLogger()


async def audit_middleware(request: Request, call_next) -> Response:
    """
    Middleware to audit all API requests.
    
    Skips health checks and metrics endpoints to reduce noise.
    """
    start_time = time.time()
    
    # Skip audit for health checks and metrics
    if request.url.path.startswith("/health") or request.url.path == "/metrics":
        response = await call_next(request)
        return response
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        error = None
    except Exception as e:
        error = str(e)
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)
        
        # Create a response object if we have an exception
        if 'response' not in dir():
            response = JSONResponse(
                status_code=500,
                content={"error": error}
            )
        
        audit_logger.log(
            request=request,
            response=response,
            duration_ms=duration_ms,
            user_id=user_id,
            username=username,
            error=error,
        )
    
    return response


def get_audit_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> list:
    """
    Retrieve audit logs.
    
    In production, this would query a database or log aggregation system.
    """
    # Placeholder - would retrieve from database/Elasticsearch/etc.
    return []
