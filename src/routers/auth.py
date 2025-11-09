"""Authentication endpoints: register, login, get current user"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from src.config import settings
from src.database import get_db
from src.models import User
from src.schemas import Token, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """
    Register a new user and set session cookie.

    Args:
        user_data: User registration data
        response: FastAPI response object (to set cookie)
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: If username or email already exists
    """
    # Check if single-user mode is enabled and a user already exists
    if settings.single_user:
        user_count = db.query(User).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is disabled in single-user mode"
            )

    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        display_name=user_data.display_name,
        bio=user_data.bio,
        password_hash=get_password_hash(user_data.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create access token and set cookie
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax"
    )

    return db_user


@router.post("/login", response_model=UserResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Login with username and password and set session cookie.

    Args:
        form_data: OAuth2 form with username and password
        response: FastAPI response object (to set cookie)
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax"
    )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.

    Args:
        current_user: Current user from JWT token

    Returns:
        Current user object
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.

    Args:
        user_update: Updated user data
        current_user: Current user from JWT token
        db: Database session

    Returns:
        Updated user object
    """
    if user_update.display_name is not None:
        current_user.display_name = user_update.display_name

    if user_update.bio is not None:
        current_user.bio = user_update.bio

    if user_update.show_heatmap is not None:
        current_user.show_heatmap = user_update.show_heatmap

    db.commit()
    db.refresh(current_user)

    return current_user


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
