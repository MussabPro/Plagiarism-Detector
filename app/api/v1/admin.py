"""
Admin API routes.
Handles user management, admin operations, and admin dashboard.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.schemas import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    PasswordReset, AdminPasswordChange, MessageResponse
)
from app.core.deps import require_admin, get_current_user
from app.core.exceptions import NotFoundError
from app.services.user_service import UserService
from app.db.models import User, UserRole

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Render admin dashboard page.
    """
    user_service = UserService(db)

    # Get all users
    users = user_service.get_all_users()

    # Get user counts by role
    student_count = user_service.count_users_by_role(UserRole.STUDENT)
    teacher_count = user_service.count_users_by_role(UserRole.TEACHER)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users,
            "student_count": student_count,
            "teacher_count": teacher_count,
            "total_users": len(users)
        }
    )


@router.get("/users", response_model=UserListResponse)
async def get_all_users_api(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to get all users (paginated).
    """
    user_service = UserService(db)
    users = user_service.get_all_users(skip=skip, limit=limit)
    total = user_service.count_users()

    return {"users": users, "total": total}


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user_api(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to create a new user.
    """
    user_service = UserService(db)
    user = user_service.create_user(user_data)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_api(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to get a specific user.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise NotFoundError(detail=f"User with ID {user_id} not found")

    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_api(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to update a user.
    """
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_data)
    return user


@router.get("/update-user/{user_id}", response_class=HTMLResponse)
async def update_user_page(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Render user update page.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise NotFoundError(detail=f"User with ID {user_id} not found")

    return templates.TemplateResponse(
        "admin/update_user.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user
        }
    )


@router.post("/update-user/{user_id}")
async def update_user_form(
    user_id: int,
    request: Request,
    username: str = Form(...),
    userid: int = Form(...),
    Fname: str = Form(...),
    Lname: str = Form(None),
    email: str = Form(...),
    PhoneNo: str = Form(None),
    Course: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Handle user update form submission.
    """
    user_service = UserService(db)
    try:
        user_data = UserUpdate(
            username=username,
            userid=userid,
            Fname=Fname,
            Lname=Lname,
            email=email,
            PhoneNo=PhoneNo,
            Course=Course,
            role=UserRole(role)
        )

        user_service.update_user(user_id, user_data)
        return RedirectResponse(url="/admin/?updated=true", status_code=303)
    except Exception as e:
        user = user_service.get_user_by_id(user_id)
        return templates.TemplateResponse(
            "admin/update_user.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "error": str(e)
            }
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user_api(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to delete a user.
    """
    user_service = UserService(db)
    user_service.delete_user(user_id)
    return {"message": f"User {user_id} deleted successfully"}


@router.get("/delete-user/{user_id}")
@router.post("/delete-user/{user_id}")
async def delete_user_form(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete user (GET or POST form submission) and redirect to admin dashboard.
    """
    user_service = UserService(db)
    user_service.delete_user(user_id)
    return RedirectResponse(url="/admin/?deleted=true", status_code=303)


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password_api(
    user_id: int,
    password_data: PasswordReset,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    API endpoint to reset user password.
    """
    user_service = UserService(db)
    user_service.reset_password(user_id, password_data.new_password)
    return {"message": "Password reset successfully"}


@router.get("/reset-password/{user_id}", response_class=HTMLResponse)
async def reset_password_page(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Render password reset page.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise NotFoundError(detail=f"User with ID {user_id} not found")

    return templates.TemplateResponse(
        "admin/reset_password.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user
        }
    )


@router.post("/reset-password/{user_id}")
async def reset_password_form(
    user_id: int,
    request: Request,
    new_password: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Handle password reset form submission."""
    try:
        user_service = UserService(db)
        user_service.reset_password(user_id, new_password)
        return RedirectResponse(url="/admin/?reset=true", status_code=303)
    except Exception as e:
        user_service2 = UserService(db)
        user = user_service2.get_user_by_id(user_id)
        return templates.TemplateResponse(
            "admin/reset_password.html",
            {
                "request": request,
                "current_user": current_user,
                "user": user,
                "error": str(e)
            }
        )


@router.post("/change-password")
async def change_admin_password_form(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Handle admin password change form (inline on dashboard)."""
    if new_password != confirm_password:
        return RedirectResponse(url="/admin/?error=Passwords+do+not+match", status_code=303)
    try:
        user_service = UserService(db)
        user_service.change_password(current_user, old_password, new_password)
        return RedirectResponse(url="/admin/?updated=true", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/?error={str(e)}", status_code=303)
