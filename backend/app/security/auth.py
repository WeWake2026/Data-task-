import base64
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
from cryptography.fernet import Fernet
from backend.app.config import settings

# Argon2id password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def _get_fernet_key() -> bytes:
    # Ensure a valid 32-byte urlsafe base64 key
    raw = hashlib.sha256(settings.TOKEN_ENCRYPTION_KEY.encode()).digest()
    return base64.urlsafe_b64encode(raw)

fernet = Fernet(_get_fernet_key())

def hash_password(password: str) -> str:
    """Hashes password using Argon2id."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates short-lived JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Generates refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    """Decodes and validates JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return {}

def encrypt_token(plain_token: str) -> str:
    """Encrypts OAuth provider tokens (refresh tokens) at rest."""
    if not plain_token:
        return ""
    return fernet.encrypt(plain_token.encode()).decode()

def decrypt_token(cipher_token: str) -> str:
    """Decrypts OAuth provider tokens when making cloud API calls."""
    if not cipher_token:
        return ""
    try:
        return fernet.decrypt(cipher_token.encode()).decode()
    except Exception:
        return ""
