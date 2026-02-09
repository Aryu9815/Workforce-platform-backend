"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
import uuid

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    email: Optional[str] = None
    permissions: List[str] = []
    exp: Optional[datetime] = None


class SecurityUtils:
    """Utility class for security operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        print('pass for hash', password, len(password))
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt."""
        return pwd_context.gen_salt()
    
    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        tenant_id: Optional[str] = None,
        permissions: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        expire = datetime.now(timezone.utc) + expires_delta
        print('EXPIRE', expire.timestamp())
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "permissions": permissions or [],
            "type": "access",
            # "exp": expire,
            "exp":  int(expire.timestamp()),
            # "iat": datetime.utcnow(),
            "iat": int(datetime.utcnow().timestamp()),
            "jti": str(uuid.uuid4())
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        user_id: str,
        tenant_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        expire = datetime.now(timezone.utc) + expires_delta
        
        to_encode = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "type": "refresh",
            # "exp": expire,
            "exp":  int(expire.timestamp()),
            # "iat": datetime.utcnow(),
            "iat": int(datetime.utcnow().timestamp()),
            "jti": str(uuid.uuid4())
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as error:
            print('JWT ERROR', error)
            return None
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify a token and return token data."""
        payload = SecurityUtils.decode_token(token)
        print('PAYLOAD', payload)
        if payload is None:
            print('payload none')
            return None
        
        # Check token type
        if payload.get("type") != token_type:
            print('type none')
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
            print('exp none')
            return None
        
        return TokenData(
            user_id=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            email=payload.get("email"),
            permissions=payload.get("permissions", []),
            exp=datetime.fromtimestamp(exp) if exp else None
        )
    
    @staticmethod
    def generate_password_reset_token(user_id: str) -> str:
        """Generate a password reset token."""
        expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode = {
            "sub": str(user_id),
            "type": "password_reset",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """Verify a password reset token and return user_id."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get("type") != "password_reset":
                return None
            
            return payload.get("sub")
        except JWTError:
            return None


# Convenience functions
hash_password = SecurityUtils.hash_password
verify_password = SecurityUtils.verify_password
create_access_token = SecurityUtils.create_access_token
create_refresh_token = SecurityUtils.create_refresh_token
decode_token = SecurityUtils.decode_token
verify_token = SecurityUtils.verify_token
