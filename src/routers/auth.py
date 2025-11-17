"""Authentication endpoints: login and logout"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.auth import authenticate_admin, create_access_token
from src.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginResponse(BaseModel):
    """Login response schema"""
    username: str
    message: str


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = None
):
    """
    Login with admin credentials from environment and set session cookie.

    Args:
        form_data: OAuth2 form with username and password
        response: FastAPI response object (to set cookie)

    Returns:
        Login success message

    Raises:
        HTTPException: If authentication fails
    """
    if not authenticate_admin(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": settings.admin_username},
        expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax"
    )

    return LoginResponse(
        username=settings.admin_username,
        message="Successfully logged in"
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout by clearing the session cookie.

    Args:
        response: FastAPI response object (to clear cookie)

    Returns:
        Success message
    """
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}
