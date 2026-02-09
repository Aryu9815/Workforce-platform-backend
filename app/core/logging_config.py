"""
Logging configuration for the application.
Creates separate log files for API, SQL, and errors.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

from app.core.config import settings


def setup_logging():
    """Setup application logging with separate log files."""
    
    # Create logs directory
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # API Log Handler - Records all API requests with timing
    api_logger = logging.getLogger("api_logger")
    api_logger.setLevel(logging.INFO)
    api_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "api.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    api_handler.setLevel(logging.INFO)
    api_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    api_handler.setFormatter(api_formatter)
    api_logger.addHandler(api_handler)
    # Prevent propagation to root
    api_logger.propagate = False
    
    # SQL Log Handler - Records all database queries
    sql_logger = logging.getLogger("sql_logger")
    sql_logger.setLevel(logging.INFO)
    sql_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "sql.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    sql_handler.setLevel(logging.INFO)
    sql_formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    sql_handler.setFormatter(sql_formatter)
    sql_logger.addHandler(sql_handler)
    sql_logger.propagate = False
    
    # Error Log Handler - Records errors and tracebacks
    error_logger = logging.getLogger("error_logger")
    error_logger.setLevel(logging.ERROR)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d\n'
        'Message: %(message)s\n'
        'Exception: %(exc_info)s\n'
        '---',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    error_logger.propagate = False
    
    # Application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)
    app_logger.propagate = False
    
    return {
        "api": api_logger,
        "sql": sql_logger,
        "error": error_logger,
        "app": app_logger
    }


class APILogger:
    """Helper class for logging API requests."""
    
    def __init__(self):
        self.logger = logging.getLogger("api_logger")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        user_id: str = None,
        tenant_id: str = None,
        message: str = ""
    ):
        """Log an API request with timing information."""
        user_str = user_id or "anonymous"
        tenant_str = tenant_id or "no-tenant"
        
        log_message = (
            f"{method} {path} | "
            f"Status: {status_code} | "
            f"Time: {response_time_ms:.2f}ms | "
            f"User: {user_str} | "
            f"Tenant: {tenant_str}"
        )
        
        if message:
            log_message += f" | {message}"
        
        self.logger.info(log_message)


class ErrorLogger:
    """Helper class for logging errors."""
    
    def __init__(self):
        self.logger = logging.getLogger("error_logger")
    
    def log_error(
        self,
        error: Exception,
        context: dict = None,
        user_id: str = None,
        request_id: str = None
    ):
        """Log an error with context."""
        context_str = ""
        if context:
            context_str = " | Context: " + ", ".join([f"{k}={v}" for k, v in context.items()])
        
        user_str = f" | User: {user_id}" if user_id else ""
        request_str = f" | Request: {request_id}" if request_id else ""
        
        self.logger.error(
            f"{type(error).__name__}: {str(error)}{context_str}{user_str}{request_str}",
            exc_info=True
        )
    
    def log_validation_error(
        self,
        errors: dict,
        user_id: str = None,
        request_id: str = None
    ):
        """Log a validation error."""
        user_str = f" | User: {user_id}" if user_id else ""
        request_str = f" | Request: {request_id}" if request_id else ""
        
        self.logger.error(
            f"Validation Error: {errors}{user_str}{request_str}"
        )


# Global logger instances
api_logger = APILogger()
error_logger = ErrorLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name)
