"""Authentication utilities: password verification, JWT tokens, and dependencies"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings

# Password hashing context (using argon2)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary to encode in the token (should include "sub" with username)
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def authenticate_admin(username: str, password: str) -> bool:
    """
    Authenticate against admin credentials from environment variables.

    Args:
        username: Username to check
        password: Plain text password to verify

    Returns:
        True if credentials match, False otherwise
    """
    if username != settings.admin_username:
        return False

    # Check if admin password is already hashed (starts with $argon2)
    if settings.admin_password.startswith("$argon2"):
        return verify_password(password, settings.admin_password)
    else:
        # Plain text password in env (not recommended but supported)
        return password == settings.admin_password


async def require_auth(request: Request) -> bool:
    """
    FastAPI dependency to require authentication.
    Validates JWT token from cookie.

    Args:
        request: FastAPI request object (to access cookies)

    Returns:
        True if authenticated

    Raises:
        HTTPException: If token is invalid or missing
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None or username != settings.admin_username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return True


async def get_auth_status(request: Request) -> bool:
    """
    FastAPI dependency to check if user is authenticated (optional).
    Returns True if authenticated, False otherwise (no exception).

    Args:
        request: FastAPI request object (to access cookies)

    Returns:
        True if authenticated, False otherwise
    """
    token = request.cookies.get("access_token")
    if not token:
        return False

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None or username != settings.admin_username:
            return False
        return True
    except JWTError:
        return False


def get_user_profile() -> dict:
    """
    Get user profile from environment configuration.

    Returns:
        Dictionary with user profile fields
    """
    return {
        "username": settings.admin_username,
        "display_name": settings.admin_display_name or settings.admin_username,
        "bio": settings.admin_bio,
        "show_heatmap": settings.admin_show_heatmap
    }
