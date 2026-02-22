"""
Authentication JSON API routes only.
Page routes (login, register) live in common.py.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import UserCreate, Token, LoginRequest, UserResponse
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.services.user_service import UserService
from app.db.models import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_api(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """JSON API login — returns JWT access token."""
    user_service = UserService(db)
    user = user_service.authenticate_user(
        login_data.username, login_data.password)

    if not user:
        raise AuthenticationError(detail="Incorrect username or password")

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_api(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """JSON API registration — creates user, returns user object."""
    user_service = UserService(db)
    return user_service.create_user(user_data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user
