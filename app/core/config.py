"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

load_dotenv()



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Multi-Tenant Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Security
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12
    
    CACHE_DB : str = "YES"
    # CORS
    CORS_ORIGINS: str | List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    CACHE_DB: str = 'NO'
    
    @field_validator("CORS_ORIGINS", mode="before")
    def fix_cors(cls, v):
        if not v:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Normalize weird characters, spaces, unicode commas, etc.
            v = v.replace(" ", "").replace("，", ",").strip()
            return v.split(",")
        raise ValueError("Invalid CORS_ORIGINS format")

    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "/tmp/uploads"
    
    # AWS S3 (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"
    
    # Email
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = 'example@example.com'
    SMTP_PASSWORD: str = 'password'
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "app/logs"
    
    # Vapid
    VAPID_PUBLIC_KEY: str
    VAPID_PRIVATE_KEY: str
    VAPID_EMAIL: str

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


# Global settings instance
settings = Settings()