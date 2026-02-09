"""Services module initialization."""
from app.services.crud import CRUDService
from app.services.auth import auth_service, AuthService

__all__ = ["CRUDService", "auth_service", "AuthService"]
