"""Rate limiting middleware and utilities."""
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from collections import defaultdict
import hashlib

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint."""
    requests: int
    window_seconds: int
    
    def __init__(self, requests: int = 100, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: int
    limit: int
    window: int


class InMemoryRateLimiter:
    """Thread-safe in-memory rate limiter."""
    
    def __init__(self):
        self._counters: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate a rate limit key."""
        return f"{endpoint}:{identifier}"
    
    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        config: RateLimitConfig
    ) -> RateLimitResult:
        """
        Check if a request is within rate limits.
        
        Args:
            identifier: Client identifier (IP, user ID, etc.)
            endpoint: API endpoint being accessed
            config: Rate limit configuration
            
        Returns:
            RateLimitResult with allow/deny decision
        """
        key = self._get_key(identifier, endpoint)
        now = time.time()
        window_start = now - config.window_seconds
        
        with self._lock:
            # Clean old entries
            if key in self._counters:
                self._counters[key] = [
                    t for t in self._counters[key]
                    if t > window_start
                ]
            
            # Check limit
            request_times = self._counters[key]
            remaining = config.requests - len(request_times)
            
            if remaining < 0:
                remaining = 0
            
            # Get oldest request time for reset calculation
            if request_times:
                oldest = min(request_times)
                reset_time = int(oldest + config.window_seconds)
            else:
                reset_time = int(now + config.window_seconds)
            
            if len(request_times) >= config.requests:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    limit=config.requests,
                    window=config.window_seconds,
                )
            
            # Record this request
            request_times.append(now)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining - 1,
                reset_time=reset_time,
                limit=config.requests,
                window=config.window_seconds,
            )
    
    def get_usage(self, identifier: str, endpoint: str) -> int:
        """Get current request count for an identifier."""
        key = self._get_key(identifier, endpoint)
        now = time.time()
        window_start = now - 60
        
        with self._lock:
            if key in self._counters:
                return len([t for t in self._counters[key] if t > window_start])
        return 0
    
    def reset(self, identifier: str, endpoint: str = None):
        """Reset rate limit for an identifier."""
        key = self._get_key(identifier, endpoint) if endpoint else identifier
        with self._lock:
            if endpoint:
                self._counters[key] = []
            else:
                keys_to_remove = [k for k in self._counters if k.startswith(f"{identifier}:")]
                for k in keys_to_remove:
                    del self._counters[k]


# Global rate limiter
_rate_limiter = InMemoryRateLimiter()


# Default rate limits by endpoint type
DEFAULT_RATE_LIMITS = {
    "default": RateLimitConfig(requests=100, window_seconds=60),
    "auth": RateLimitConfig(requests=10, window_seconds=60),
    "voice": RateLimitConfig(requests=50, window_seconds=60),
    "health": RateLimitConfig(requests=200, window_seconds=60),
}


def get_client_identifier(request: Request) -> str:
    """Extract client identifier from request."""
    # Check for X-Forwarded-For header (from proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to client host
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(
    request: Request,
    call_next,
    endpoint_type: str = "default"
):
    """
    Middleware to apply rate limiting.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        endpoint_type: Type of endpoint for rate limit selection
    """
    config = DEFAULT_RATE_LIMITS.get(endpoint_type, DEFAULT_RATE_LIMITS["default"])
    identifier = get_client_identifier(request)
    
    result = _rate_limiter.check_rate_limit(
        identifier=identifier,
        endpoint=request.url.path,
        config=config
    )
    
    # Add rate limit headers
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_time),
    }
    
    if not result.allowed:
        logger.warning(
            f"Rate limit exceeded for {identifier} on {request.url.path}",
            extra={"identifier": identifier, "endpoint": request.url.path}
        )
        
        return JSONResponse(
            status_code=429,
            headers=headers,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": result.reset_time - int(time.time()),
            }
        )
    
    response = await call_next(request)
    
    # Add headers to response
    for key, value in headers.items():
        response.headers[key] = value
    
    return response


class RateLimitDepend:
    """Dependency for rate limiting on specific routes."""
    
    def __init__(self, endpoint_type: str = "default"):
        self.endpoint_type = endpoint_type
    
    async def __call__(
        self,
        request: Request
    ) -> Tuple[str, RateLimitConfig]:
        """Check rate limit and return identifier and config."""
        config = DEFAULT_RATE_LIMITS.get(
            self.endpoint_type,
            DEFAULT_RATE_LIMITS["default"]
        )
        
        identifier = get_client_identifier(request)
        
        result = _rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            config=config
        )
        
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after": result.reset_time - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_time),
                    "Retry-After": str(result.reset_time - int(time.time())),
                }
            )
        
        return identifier, config


def create_rate_limit_headers(result: RateLimitResult) -> Dict[str, str]:
    """Create rate limit headers from result."""
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_time),
    }


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


def configure_rate_limits(configs: Dict[str, RateLimitConfig]):
    """Configure rate limits for different endpoint types."""
    DEFAULT_RATE_LIMITS.update(configs)


# Redis-backed rate limiter (for distributed systems)
class RedisRateLimiter:
    """Redis-based rate limiter for horizontal scaling."""
    
    def __init__(self, redis_url: str = None):
        self._redis_url = redis_url or __import__('os').getenv('REDIS_URL')
        self._redis = None
    
    def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None and self._redis_url:
            import redis
            self._redis = redis.from_url(self._redis_url)
        return self._redis
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        config: RateLimitConfig
    ) -> RateLimitResult:
        """Check rate limit using Redis."""
        redis = self._get_redis()
        
        if redis is None:
            return _rate_limiter.check_rate_limit(identifier, endpoint, config)
        
        key = f"ratelimit:{endpoint}:{identifier}"
        now = time.time()
        window_start = now - config.window_seconds
        
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, config.window_seconds)
        results = await pipe.execute()
        
        current_count = results[2]
        remaining = max(0, config.requests - current_count)
        
        if current_count >= config.requests:
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            reset_time = int(oldest[0][1] + config.window_seconds) if oldest else int(now + config.window_seconds)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                limit=config.requests,
                window=config.window_seconds,
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining - 1,
            reset_time=int(now + config.window_seconds),
            limit=config.requests,
            window=config.window_seconds,
        )
