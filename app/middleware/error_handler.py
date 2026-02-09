"""
Global error handling middleware.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import traceback
import uuid

from app.core.logging_config import error_logger
from app.core.config import settings


class ErrorResponse:
    """Standardized error response structure."""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str = None,
        details: dict = None,
        request_id: str = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code or f"ERR_{status_code}"
        self.details = details or {}
        self.request_id = request_id or str(uuid.uuid4())[:8]
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "request_id": self.request_id
            }
        }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Catch and handle all exceptions."""
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            return response
            
        except StarletteHTTPException as exc:
            return self._handle_http_exception(exc, request_id)
            
        except RequestValidationError as exc:
            return self._handle_validation_error(exc, request_id)
            
        except IntegrityError as exc:
            return self._handle_integrity_error(exc, request_id)
            
        except SQLAlchemyError as exc:
            return self._handle_database_error(exc, request_id)
            
        except Exception as exc:
            return self._handle_generic_error(exc, request_id)
    
    def _handle_http_exception(
        self,
        exc: StarletteHTTPException,
        request_id: str
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        error_response = ErrorResponse(
            status_code=exc.status_code,
            message=exc.detail,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict()
        )
    
    def _handle_validation_error(
        self,
        exc: RequestValidationError,
        request_id: str
    ) -> JSONResponse:
        """Handle request validation errors."""
        # Format validation errors
        errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors[field] = error["msg"]
        
        error_response = ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation error",
            error_code="ERR_VALIDATION",
            details={"fields": errors},
            request_id=request_id
        )
        
        # Log validation error
        error_logger.log_validation_error(errors, request_id=request_id)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.to_dict()
        )
    
    def _handle_integrity_error(
        self,
        exc: IntegrityError,
        request_id: str
    ) -> JSONResponse:
        """Handle database integrity errors."""
        error_str = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        # Determine specific error type
        if "unique constraint" in error_str.lower():
            message = "A record with this information already exists"
            error_code = "ERR_DUPLICATE"
        elif "foreign key" in error_str.lower():
            message = "Referenced record does not exist"
            error_code = "ERR_FOREIGN_KEY"
        else:
            message = "Database constraint violation"
            error_code = "ERR_INTEGRITY"
        
        error_response = ErrorResponse(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            error_code=error_code,
            request_id=request_id
        )
        
        # Log error
        error_logger.log_error(exc, request_id=request_id)
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response.to_dict()
        )
    
    def _handle_database_error(
        self,
        exc: SQLAlchemyError,
        request_id: str
    ) -> JSONResponse:
        """Handle database errors."""
        error_response = ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Database error occurred",
            error_code="ERR_DATABASE",
            request_id=request_id
        )
        
        # Log error with details
        error_logger.log_error(exc, request_id=request_id)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict()
        )
    
    def _handle_generic_error(
        self,
        exc: Exception,
        request_id: str
    ) -> JSONResponse:
        """Handle unexpected errors."""
        # Log full traceback
        error_logger.log_error(
            exc,
            request_id=request_id
        )
        
        # Return generic error in production
        if not settings.DEBUG:
            message = "An unexpected error occurred"
        else:
            message = str(exc)
        
        error_response = ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code="ERR_INTERNAL",
            details={"traceback": traceback.format_exc()} if settings.DEBUG else {},
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict()
        )


# Exception handlers for FastAPI
def add_exception_handlers(app):
    """Add exception handlers to FastAPI app."""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
        
        error_response = ErrorResponse(
            status_code=exc.status_code,
            message=exc.detail,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
        
        errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors[field] = error["msg"]
        
        error_response = ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation error",
            error_code="ERR_VALIDATION",
            details={"fields": errors},
            request_id=request_id
        )
        
        error_logger.log_validation_error(errors, request_id=request_id)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.to_dict()
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
        
        error_response = ErrorResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(exc),
            error_code="ERR_BAD_REQUEST",
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.to_dict()
        )
