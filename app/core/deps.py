"""
FastAPI dependency injection utilities.
Provides dependencies for authentication, authorization, and database access.
"""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.database import get_db
from app.db.models import User, UserRole


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract token from Authorization header or cookie.

    Args:
        request: FastAPI request object

    Returns:
        Token string or None
    """
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")

    # Try cookie
    cookie_value = request.cookies.get("access_token")
    if cookie_value and cookie_value.startswith("Bearer "):
        return cookie_value.replace("Bearer ", "")

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Current user object

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = get_token_from_request(request)

    if not token:
        raise AuthenticationError(detail="Not authenticated")

    # Decode token
    payload = decode_access_token(token)
    username: str = payload.get("sub")

    if username is None:
        raise AuthenticationError(detail="Could not validate credentials")

    # Get user from database
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise AuthenticationError(detail="User not found")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    Can be extended to check user.is_active field if added.

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user
    """
    # Future: Add is_active check here if needed
    return current_user


def require_role(required_role: UserRole):
    """
    Factory function to create role-based dependencies.

    Args:
        required_role: Role required to access the endpoint

    Returns:
        Dependency function that checks user role
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role:
            raise PermissionDeniedError(
                detail=f"This endpoint requires {required_role.value} role"
            )
        return current_user

    return role_checker


# Pre-configured role dependencies
require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER)
require_student = require_role(UserRole.STUDENT)


def require_teacher_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to check if user is teacher or admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if they are teacher or admin

    Raises:
        PermissionDeniedError: If user is not teacher or admin
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise PermissionDeniedError(
            detail="This endpoint requires Teacher or Admin role"
        )
    return current_user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns user if authenticated, None otherwise.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    token = get_token_from_request(request)

    if not token:
        return None

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")

        if username is None:
            return None

        user = db.query(User).filter(User.username == username).first()
        return user
    except:
        return None
