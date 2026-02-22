"""
Common routes: public pages (home, login, register, logout) and shared file endpoints.
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app.db.schemas import UserResponse, UserCreate
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, PermissionDeniedError, DuplicateError
from app.core.security import create_access_token
from app.core.config import settings
from app.services.assignment_service import AssignmentService
from app.services.user_service import UserService
from app.db.models import User, UserRole

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Public pages ──────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Landing page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login form — set cookie and redirect by role."""
    user_service = UserService(db)
    user = user_service.authenticate_user(username, password)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Incorrect username or password"}
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    if user.role.value == "Admin":
        redirect_url = "/admin/"
    elif user.role.value == "Teacher":
        redirect_url = "/teacher/dashboard"
    else:
        redirect_url = "/student/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_form(
    request: Request,
    username: str = Form(...),
    userid: int = Form(...),
    fname: str = Form(..., alias="Fname"),
    lname: str = Form(None, alias="Lname"),
    email: str = Form(...),
    phone: str = Form(..., alias="PhoneNo"),
    course: str = Form(..., alias="Course"),
    role: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle registration form submission."""
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"}
        )

    if role not in ("Student", "Teacher"):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Invalid role selected"}
        )

    try:
        user_service = UserService(db)
        user_data = UserCreate(
            username=username,
            userid=userid,
            Fname=fname,
            Lname=lname,
            email=email,
            PhoneNo=phone,
            Course=course,
            role=UserRole(role),
            password=password
        )
        user_service.create_user(user_data)
        return RedirectResponse(url="/login?registered=true", status_code=303)
    except DuplicateError as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": e.detail}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Registration failed: {str(e)}"}
        )


@router.get("/logout")
async def logout():
    """Clear auth cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# ── Authenticated shared routes ────────────────────────────────────────────────

@router.get("/profile")
async def profile_redirect(current_user: User = Depends(get_current_user)):
    """Redirect profile requests to the appropriate role dashboard."""
    if current_user.role.value == "Teacher":
        return RedirectResponse(url="/teacher/dashboard")
    elif current_user.role.value == "Admin":
        return RedirectResponse(url="/admin/")
    return RedirectResponse(url="/student/dashboard")


@router.get("/api/v1/users/profile", response_model=UserResponse)
async def get_profile_api(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/download-assignment/{assignment_id}")
async def download_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a student submission file (role-restricted)."""
    assignment_service = AssignmentService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)

    if not assignment:
        raise NotFoundError(detail=f"Assignment {assignment_id} not found")

    if current_user.role.value == "Student":
        if assignment.user_id != current_user.id:
            raise PermissionDeniedError(
                detail="You can only download your own assignments")
    elif current_user.role.value == "Teacher":
        if assignment.course != current_user.Course:
            raise PermissionDeniedError(
                detail="You can only download assignments from your course")

    return Response(
        content=assignment.file_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={assignment.filename}"}
    )


@router.get("/download-assignment-question/{course}")
async def download_question(
    course: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the question file for a course."""
    assignment_service = AssignmentService(db)
    question_file = assignment_service.get_question_file_by_course(course)

    if not question_file:
        raise NotFoundError(detail=f"No question file for course {course}")

    if current_user.role.value == "Student" and current_user.Course != course:
        raise PermissionDeniedError(detail="Access denied")

    return Response(
        content=question_file.file_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={question_file.filename}"}
    )
