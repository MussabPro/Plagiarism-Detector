"""
Database models for the plagiarism detection system.
Enhanced with proper constraints, indexes, and relationships.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    LargeBinary, ForeignKey, Index, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.db.database import Base


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""
    NOT_CHECKED = "Not Checked"
    CHECKED = "Checked"
    PENDING = "Pending"


class User(Base):
    """User model for admin, teachers, and students."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    userid = Column(Integer, nullable=False)  # Student/Teacher ID
    Fname = Column(String(50), nullable=False)
    Lname = Column(String(50), nullable=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    PhoneNo = Column(String(12), nullable=False)
    Course = Column(String(5), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Increased size for bcrypt

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assignments = relationship(
        "Assignment", back_populates="user", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_role_course', 'role', 'Course'),
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class AssignmentQuestionFile(Base):
    """Assignment question files uploaded by teachers."""

    __tablename__ = "assignment_question_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    course = Column(String(5), nullable=False, index=True)
    plagiarism_threshold = Column(Float, default=40.0)
    include_references = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AssignmentQuestionFile {self.filename} for {self.course}>"


class Assignment(Base):
    """Student assignment submissions."""

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    course = Column(String(5), nullable=False, index=True)
    timeuploaded = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SQLEnum(AssignmentStatus),
                    default=AssignmentStatus.NOT_CHECKED)
    comment = Column(String(500), nullable=True)
    totalmarks = Column(Integer, nullable=True)
    obtmarks = Column(Integer, nullable=True)

    # Changed from PickleType to JSON for security
    plagiarism_report = Column(JSON, nullable=True)
    plagiarism_percentage = Column(Float, nullable=True)
    auto_graded = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="assignments")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_assignment_course_status', 'course', 'status'),
        Index('idx_assignment_user_course', 'user_id', 'course'),
    )

    def __repr__(self):
        return f"<Assignment {self.filename} by user {self.user_id}>"


class AssignmentDueDate(Base):
    """Due dates for assignments by course."""

    __tablename__ = "assignment_due_dates"

    id = Column(Integer, primary_key=True, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    course = Column(String(5), nullable=False, unique=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AssignmentDueDate {self.course} - {self.due_date}>"
