"""
Authentication middleware for JWT token validation.
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List
import time

from app.core.security import verify_token
from app.db.base import set_tenant_context, clear_tenant_context
from app.core.logging_config import api_logger, error_logger

security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and tenant context."""
    
    def __init__(
        self,
        app,
        exclude_paths: List[str] = None,
        public_paths: List[str] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]
        self.public_paths = public_paths or []
    
    async def dispatch(self, request: Request, call_next):
        """Process each request for authentication."""
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        # Skip authentication for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            response = await call_next(request)
            return response
        
        # Extract and validate token
        token = self._extract_token(request)
        
        if not token:
            # Check if path is public
            if any(path.startswith(public) for public in self.public_paths):
                response = await call_next(request)
                return response
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify token
        token_data = verify_token(token, token_type="access")
        if not token_data:
            if any(path.startswith(public) for public in self.public_paths):
                return await call_next(request)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Set user and tenant in request state
        request.state.common_id = token_data.user_id
        request.state.common_id = token_data.common_id
        request.state.user_email = token_data.email
        request.state.tenant_id = token_data.tenant_id
        request.state.permissions = token_data.permissions
        
        # Set tenant context for database queries
        if token_data.tenant_id:
            set_tenant_context(token_data.tenant_id)
        
        # Process request
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear tenant context
            clear_tenant_context()
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None
        
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Middleware to resolve tenant from various sources."""
    
    async def dispatch(self, request: Request, call_next):
        """Resolve tenant ID from headers or JWT."""
        # Priority: JWT token > X-Tenant-ID header > subdomain
        tenant_id = None
        
        # Check JWT token first (set by AuthMiddleware)
        if hasattr(request.state, 'tenant_id') and request.state.tenant_id:
            tenant_id = request.state.tenant_id
        
        # Check X-Tenant-ID header
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")
        
        # Check subdomain (e.g., tenant.example.com)
        if not tenant_id:
            host = request.headers.get("Host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                # TODO: Resolve tenant ID from subdomain
                pass
        
        # Set tenant context
        if tenant_id:
            request.state.tenant_id = tenant_id
            set_tenant_context(tenant_id)
        
        try:
            response = await call_next(request)
            
            # Add tenant ID to response headers for debugging
            if tenant_id:
                response.headers["X-Tenant-ID"] = tenant_id
            
            return response
        finally:
            clear_tenant_context()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response details."""
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        user_id = getattr(request.state, 'user_id', None)
        tenant_id = getattr(request.state, 'tenant_id', None)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Log the request
            api_logger.log_request(
                method=method,
                path=path,
                status_code=response.status_code,
                response_time_ms=response_time,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            # Add timing header
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            
            return response
            
        except Exception as e:
            # Log error
            response_time = (time.time() - start_time) * 1000
            
            error_logger.log_error(
                error=e,
                context={"path": path, "method": method},
                user_id=user_id,
                request_id=request.headers.get("X-Request-ID")
            )
            
            raise


class CORSMiddleware:
    """Custom CORS middleware with tenant header support."""
    
    @staticmethod
    def get_cors_headers(request: Request) -> dict:
        """Get CORS headers based on request origin."""
        from app.core.config import settings
        
        origin = request.headers.get("Origin", "")
        
        # Check if origin is allowed
        allowed_origins = settings.CORS_ORIGINS
        if "*" in allowed_origins or origin in allowed_origins:
            return {
                "Access-Control-Allow-Origin": origin or "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Tenant-ID, X-Request-ID",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600"
            }
        
        return {}


def get_current_user_id(request: Request) -> Optional[str]:
    """Get current user ID from request state."""
    return getattr(request.state, 'user_id', None)


def get_current_tenant_id(request: Request) -> Optional[str]:
    """Get current tenant ID from request state."""
    return getattr(request.state, 'tenant_id', None)


def get_current_user_permissions(request: Request) -> List[str]:
    """Get current user permissions from request state."""
    return getattr(request.state, 'permissions', [])


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions."""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_permissions = get_current_user_permissions(request)
            
            # Check if user has any of the required permissions
            if not any(perm in user_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
