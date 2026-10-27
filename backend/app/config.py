import os
from pydantic import BaseModel
from typing import List

class Settings(BaseModel):
    PROJECT_NAME: str = "Secure Cloud Transfer Manager"
    VERSION: str = "2.4.0"
    API_V1_STR: str = "/api/v1"
    
    # Security & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sctm_super_secure_enterprise_secret_key_9831974102948123_very_long")
    TOKEN_ENCRYPTION_KEY: str = os.getenv("TOKEN_ENCRYPTION_KEY", "b3BlbnNzbCByYW5kIC1iYXNlNjQgMzIgZHVtbXlrZXkxMjM0")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = "HS256"
    
    # Cookie Configuration
    SESSION_COOKIE_NAME: str = "sctm_session"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = "lax"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sctm_enterprise.db")
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Rate Limiting
    AUTH_RATE_LIMIT_PER_MINUTE: int = 15
    
    # OAuth Provider Client Configuration (Environment or Admin Configured)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/accounts/google/callback")
    
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_REDIRECT_URI: str = os.getenv("MICROSOFT_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/accounts/onedrive/callback")
    
    DROPBOX_CLIENT_ID: str = os.getenv("DROPBOX_CLIENT_ID", "")
    DROPBOX_CLIENT_SECRET: str = os.getenv("DROPBOX_CLIENT_SECRET", "")
    DROPBOX_REDIRECT_URI: str = os.getenv("DROPBOX_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/accounts/dropbox/callback")

settings = Settings()
