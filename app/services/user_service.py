"""
User service for user management operations.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import User, UserRole
from app.db.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import NotFoundError, DuplicateError, ValidationError

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email address

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User objects
        """
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_users_by_role(self, role: UserRole, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get users by role.

        Args:
            role: User role
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User objects
        """
        return self.db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

    def get_users_by_course(self, course: str, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get users by course.

        Args:
            course: Course code
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User objects
        """
        return self.db.query(User).filter(User.Course == course).offset(skip).limit(limit).all()

    def get_students_by_course(self, course: str) -> List[User]:
        """
        Get all students in a specific course.

        Args:
            course: Course code

        Returns:
            List of student User objects
        """
        return self.db.query(User).filter(
            User.Course == course,
            User.role == UserRole.STUDENT
        ).all()

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created User object

        Raises:
            DuplicateError: If username or email already exists
        """
        # Check for existing username
        if self.get_user_by_username(user_data.username):
            raise DuplicateError(
                detail=f"Username '{user_data.username}' already exists")

        # Check for existing email
        if self.get_user_by_email(user_data.email):
            raise DuplicateError(
                detail=f"Email '{user_data.email}' already exists")

        try:
            # Hash password
            hashed_password = get_password_hash(user_data.password)

            # Create user
            user = User(
                username=user_data.username,
                userid=user_data.userid,
                Fname=user_data.Fname,
                Lname=user_data.Lname,
                email=user_data.email,
                PhoneNo=user_data.PhoneNo,
                Course=user_data.Course,
                role=user_data.role,
                password=hashed_password
            )

            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"User created: {user.username} ({user.role})")
            return user

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {str(e)}")
            raise DuplicateError(
                detail="User with this information already exists")

    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Update an existing user.

        Args:
            user_id: User ID
            user_data: User update data

        Returns:
            Updated User object

        Raises:
            NotFoundError: If user not found
            DuplicateError: If username or email conflicts
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(detail=f"User with ID {user_id} not found")

        # Check for username conflicts
        if user_data.username and user_data.username != user.username:
            existing = self.get_user_by_username(user_data.username)
            if existing:
                raise DuplicateError(
                    detail=f"Username '{user_data.username}' already exists")

        # Check for email conflicts
        if user_data.email and user_data.email != user.email:
            existing = self.get_user_by_email(user_data.email)
            if existing:
                raise DuplicateError(
                    detail=f"Email '{user_data.email}' already exists")

        try:
            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            self.db.commit()
            self.db.refresh(user)

            logger.info(f"User updated: {user.username}")
            return user

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update user: {str(e)}")
            raise DuplicateError(
                detail="User update conflicts with existing data")

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(detail=f"User with ID {user_id} not found")

        try:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"User deleted: {user.username}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete user: {str(e)}")
            raise

    def reset_password(self, user_id: int, new_password: str) -> User:
        """
        Reset user password.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            Updated User object

        Raises:
            NotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(detail=f"User with ID {user_id} not found")

        try:
            user.password = get_password_hash(new_password)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Password reset for user: {user.username}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset password: {str(e)}")
            raise

    def change_password(self, user: User, old_password: str, new_password: str) -> User:
        """
        Change user password (with verification).

        Args:
            user: User object
            old_password: Current password
            new_password: New password

        Returns:
            Updated User object

        Raises:
            ValidationError: If old password is incorrect
        """
        if not verify_password(old_password, user.password):
            raise ValidationError(detail="Current password is incorrect")

        try:
            user.password = get_password_hash(new_password)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Password changed for user: {user.username}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to change password: {str(e)}")
            raise

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.password):
            return None

        return user

    def count_users(self) -> int:
        """
        Get total count of users.

        Returns:
            Total number of users
        """
        return self.db.query(User).count()

    def count_users_by_role(self, role: UserRole) -> int:
        """
        Get count of users by role.

        Args:
            role: User role

        Returns:
            Number of users with the specified role
        """
        return self.db.query(User).filter(User.role == role).count()
