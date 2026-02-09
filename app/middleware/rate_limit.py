"""
Rate limiting middleware using Redis.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Optional, Dict
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import error_logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window."""
    
    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        requests_per_minute: int = None,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS
        self.window_size = settings.RATE_LIMIT_WINDOW
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        path = request.url.path
        
        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Skip if Redis is not available
        if not self.redis:
            return await call_next(request)
        
        # Get client identifier (user ID or IP address)
        client_id = self._get_client_id(request)
        key = f"rate_limit:{client_id}"
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(key)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(int(reset_time - time.time()))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use user ID if authenticated
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    async def _check_rate_limit(self, key: str) -> tuple:
        """Check if request is within rate limit using sliding window."""
        now = time.time()
        window_start = now - self.window_size
        
        try:
            # Remove old entries outside the window
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            current_count = await self.redis.zcard(key)
            
            if current_count >= self.requests_per_minute:
                # Get oldest request time for reset calculation
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                reset_time = oldest[0][1] + self.window_size if oldest else now + self.window_size
                return False, 0, reset_time
            
            # Add current request
            await self.redis.zadd(key, {str(now): now})
            
            # Set expiry on the key
            await self.redis.expire(key, self.window_size)
            
            remaining = self.requests_per_minute - current_count - 1
            reset_time = now + self.window_size
            
            return True, remaining, reset_time
            
        except Exception as e:
            error_logger.log_error(e, {"key": key})
            # Allow request if Redis fails
            return True, self.requests_per_minute, now + self.window_size


class RateLimiter:
    """Standalone rate limiter for specific endpoints."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple:
        """Check if action is allowed under rate limit."""
        now = time.time()
        window_start = now - window
        
        try:
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            results = await pipe.execute()
            
            current_count = results[1]
            
            if current_count >= limit:
                return False, 0, now + window
            
            remaining = limit - current_count - 1
            return True, remaining, now + window
            
        except Exception:
            # Allow on error
            return True, limit, now + window
    
    async def check_login_attempts(
        self,
        identifier: str,
        max_attempts: int = 5,
        window: int = 900  # 15 minutes
    ) -> bool:
        """Check if login attempts are within limit."""
        key = f"login_attempts:{identifier}"
        allowed, _, _ = await self.is_allowed(key, max_attempts, window)
        return allowed
    
    async def record_login_attempt(self, identifier: str):
        """Record a failed login attempt."""
        key = f"login_attempts:{identifier}"
        now = time.time()
        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, 900)
    
    async def reset_login_attempts(self, identifier: str):
        """Reset login attempts counter."""
        key = f"login_attempts:{identifier}"
        await self.redis.delete(key)


# Simple in-memory rate limiter for development
class InMemoryRateLimiter:
    """In-memory rate limiter for development/testing."""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple:
        """Check if action is allowed."""
        now = time.time()
        window_start = now - window
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                ts for ts in self.requests[key]
                if ts > window_start
            ]
        else:
            self.requests[key] = []
        
        current_count = len(self.requests[key])
        
        if current_count >= limit:
            return False, 0, now + window
        
        self.requests[key].append(now)
        remaining = limit - current_count - 1
        
        return True, remaining, now + window
