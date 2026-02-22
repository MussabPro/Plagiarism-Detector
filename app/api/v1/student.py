"""
Student routes — all under /student prefix.
"""
from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import AssignmentResponse, AssignmentListResponse
from app.core.deps import require_student
from app.core.exceptions import NotFoundError
from app.services.assignment_service import AssignmentService
from app.db.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def student_dashboard(
    request: Request,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Student dashboard — shows submission status and quick submit form."""
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_user(current_user.id)
    question_file = assignment_service.get_question_file_by_course(
        current_user.Course)
    due_date = assignment_service.get_due_date(current_user.Course)
    is_due_date_passed = assignment_service.is_due_date_passed(
        current_user.Course)

    return templates.TemplateResponse(
        "student/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "assignments": assignments,
            "question_file": question_file,
            "due_date": due_date,
            "is_due_date_passed": is_due_date_passed,
            "total_assignments": len(assignments)
        }
    )


@router.get("/assignment", response_class=HTMLResponse)
async def assignment_page(
    request: Request,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Assignment details — download question and submit answer."""
    assignment_service = AssignmentService(db)
    question_file = assignment_service.get_question_file_by_course(
        current_user.Course)
    due_date = assignment_service.get_due_date(current_user.Course)
    is_due_date_passed = assignment_service.is_due_date_passed(
        current_user.Course)

    # Redirect to dashboard which contains the submission form
    return RedirectResponse(url="/student/dashboard")


@router.post("/submit")
async def submit_assignment_form(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Handle assignment file upload form submission."""
    try:
        assignment_service = AssignmentService(db)
        await assignment_service.submit_assignment(file, current_user.id, current_user.Course)
        return RedirectResponse(url="/student/dashboard?submitted=true", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/student/dashboard?error={str(e)}", status_code=303)


@router.get("/result", response_class=HTMLResponse)
async def result_page(
    request: Request,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """View plagiarism results and grades for all submissions."""
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_user(current_user.id)

    return templates.TemplateResponse(
        "student/result.html",
        {
            "request": request,
            "current_user": current_user,
            "assignments": assignments,
        }
    )


# ── JSON API endpoints (kept for API consumers) ────────────────────────────────

@router.post("/api/assignments", response_model=AssignmentResponse, status_code=201)
async def submit_assignment_api(
    file: UploadFile = File(...),
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    return await assignment_service.submit_assignment(file, current_user.id, current_user.Course)


@router.get("/api/assignments", response_model=AssignmentListResponse)
async def get_my_assignments_api(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_user(current_user.id)
    return {"assignments": assignments, "total": len(assignments)}


@router.get("/api/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment_details_api(
    assignment_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)
    if not assignment or assignment.user_id != current_user.id:
        raise NotFoundError(detail="Assignment not found")
    return assignment
