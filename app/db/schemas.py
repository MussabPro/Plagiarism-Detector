"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    ADMIN = "Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"


class AssignmentStatus(str, Enum):
    NOT_CHECKED = "Not Checked"
    CHECKED = "Checked"
    PENDING = "Pending"


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


# User Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    userid: int = Field(..., gt=0)
    Fname: str = Field(..., min_length=1, max_length=50)
    Lname: Optional[str] = Field(None, max_length=50)
    email: EmailStr
    PhoneNo: str = Field(..., pattern=r'^\d{10,12}$')
    Course: str = Field(..., min_length=1, max_length=5)
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    userid: Optional[int] = Field(None, gt=0)
    Fname: Optional[str] = Field(None, min_length=1, max_length=50)
    Lname: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    PhoneNo: Optional[str] = Field(None, pattern=r'^\d{10,12}$')
    Course: Optional[str] = Field(None, min_length=1, max_length=5)
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int


# Password Schemas
class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)


class AdminPasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate passwords match."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Assignment Question Schemas
class AssignmentQuestionCreate(BaseModel):
    course: str = Field(..., min_length=1, max_length=5)
    plagiarism_threshold: float = Field(default=40.0, ge=0, le=100)
    include_references: bool = True


class AssignmentQuestionResponse(BaseModel):
    id: int
    filename: str
    course: str
    plagiarism_threshold: float
    include_references: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Assignment Schemas
class AssignmentUpload(BaseModel):
    course: str = Field(..., min_length=1, max_length=5)


class AssignmentResponse(BaseModel):
    id: int
    filename: str
    user_id: int
    course: str
    timeuploaded: datetime
    status: AssignmentStatus
    comment: Optional[str] = None
    totalmarks: Optional[int] = None
    obtmarks: Optional[int] = None
    plagiarism_percentage: Optional[float] = None
    auto_graded: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponse]
    total: int


class AssignmentGrade(BaseModel):
    totalmarks: int = Field(..., ge=0, le=100)
    obtmarks: int = Field(..., ge=0, le=100)
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator('obtmarks')
    @classmethod
    def validate_marks(cls, v: int, info) -> int:
        """Validate obtained marks don't exceed total marks."""
        if 'totalmarks' in info.data and v > info.data['totalmarks']:
            raise ValueError('Obtained marks cannot exceed total marks')
        return v


# Plagiarism Schemas
class PlagiarismCheckRequest(BaseModel):
    exclude_references: bool = False
    exclude_quotes: bool = False


class PlagiarismMatch(BaseModel):
    assignment_id: int
    filename: str
    user_name: str
    similarity: float


class ExternalSource(BaseModel):
    url: str
    title: str
    snippet: str


class PlagiarismReportResponse(BaseModel):
    assignment_id: int
    filename: str
    plagiarism_percentage: float
    matches: List[PlagiarismMatch]
    external_sources: List[ExternalSource]
    threshold: float
    passed: bool
    checked_at: datetime


# Due Date Schemas
class DueDateUpdate(BaseModel):
    course: str = Field(..., min_length=1, max_length=5)
    due_date: Optional[datetime] = None


class DueDateResponse(BaseModel):
    id: int
    course: str
    due_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# General Response Schemas
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
