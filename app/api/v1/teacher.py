"""
Teacher routes — all under /teacher prefix.
"""
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.db.schemas import (
    AssignmentQuestionResponse, AssignmentListResponse,
    AssignmentGrade, PlagiarismCheckRequest, PlagiarismReportResponse,
    DueDateUpdate, MessageResponse
)
from app.core.deps import require_teacher
from app.core.exceptions import NotFoundError
from app.services.assignment_service import AssignmentService
from app.services.plagiarism_service import PlagiarismService
from app.db.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ── Pages ──────────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_course(
        current_user.Course)
    question_file = assignment_service.get_question_file_by_course(
        current_user.Course)
    due_date = assignment_service.get_due_date(current_user.Course)
    total = len(assignments)
    checked = assignment_service.count_checked_assignments_by_course(
        current_user.Course)

    return templates.TemplateResponse(
        "teacher/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "assignments": assignments,
            "question_file": question_file,
            "due_date": due_date,
            "total_assignments": total,
            "checked_assignments": checked,
            "unchecked_assignments": total - checked,
        }
    )


@router.get("/create-assignment", response_class=HTMLResponse)
async def create_assignment_page(
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    question_file = assignment_service.get_question_file_by_course(
        current_user.Course)
    due_date = assignment_service.get_due_date(current_user.Course)

    return templates.TemplateResponse(
        "teacher/create_assignment.html",
        {
            "request": request,
            "current_user": current_user,
            "question_file": question_file,
            "due_date": due_date,
        }
    )


@router.get("/submissions", response_class=HTMLResponse)
async def submissions_page(
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_course(
        current_user.Course)

    return templates.TemplateResponse(
        "teacher/submissions.html",
        {
            "request": request,
            "current_user": current_user,
            "assignments": assignments,
        }
    )


@router.get("/plagiarism/{assignment_id}", response_class=HTMLResponse)
async def plagiarism_check_page(
    assignment_id: int,
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)
    if not assignment or assignment.course != current_user.Course:
        raise NotFoundError(detail="Assignment not found")

    return templates.TemplateResponse(
        "teacher/plagiarism_check.html",
        {"request": request, "current_user": current_user, "assignment": assignment}
    )


@router.get("/plagiarism-report/{assignment_id}", response_class=HTMLResponse)
async def plagiarism_report_page(
    assignment_id: int,
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    plagiarism_service = PlagiarismService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)
    if not assignment or assignment.course != current_user.Course:
        raise NotFoundError(detail="Assignment not found")
    report = plagiarism_service.get_report(assignment_id)

    return templates.TemplateResponse(
        "teacher/plagiarism_report.html",
        {"request": request, "current_user": current_user,
            "assignment": assignment, "report": report}
    )


@router.get("/grade/{assignment_id}", response_class=HTMLResponse)
async def grade_page(
    assignment_id: int,
    request: Request,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)
    if not assignment or assignment.course != current_user.Course:
        raise NotFoundError(detail="Assignment not found")

    return templates.TemplateResponse(
        "teacher/grade.html",
        {"request": request, "current_user": current_user, "assignment": assignment}
    )


# ── Form handlers ──────────────────────────────────────────────────────────────

@router.post("/upload-question")
async def upload_question_form(
    request: Request,
    file: UploadFile = File(...),
    plagiarism_threshold: float = Form(40.0),
    include_references: bool = Form(False),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    try:
        assignment_service = AssignmentService(db)
        await assignment_service.upload_question_file(
            file, current_user.Course, plagiarism_threshold, include_references
        )
        return RedirectResponse(url="/teacher/dashboard?uploaded=true", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/teacher/create-assignment?error={str(e)}", status_code=303)


@router.post("/update-due-date")
async def set_due_date_form(
    request: Request,
    due_date: Optional[str] = Form(None),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    try:
        assignment_service = AssignmentService(db)
        due_date_obj = datetime.fromisoformat(due_date) if due_date else None
        assignment_service.set_due_date(current_user.Course, due_date_obj)
        return RedirectResponse(url="/teacher/dashboard?due_date_set=true", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/teacher/dashboard?error={str(e)}", status_code=303)


@router.post("/plagiarism/{assignment_id}")
async def run_plagiarism_form(
    assignment_id: int,
    request: Request,
    exclude_references: bool = Form(False),
    exclude_quotes: bool = Form(False),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    try:
        plagiarism_service = PlagiarismService(db)
        plagiarism_service.check_plagiarism(
            assignment_id, exclude_references, exclude_quotes)
        return RedirectResponse(url=f"/teacher/plagiarism-report/{assignment_id}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/teacher/dashboard?error={str(e)}", status_code=303)


@router.post("/grade/{assignment_id}")
async def grade_form(
    assignment_id: int,
    request: Request,
    totalmarks: int = Form(...),
    obtmarks: int = Form(...),
    comment: Optional[str] = Form(None),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    try:
        assignment_service = AssignmentService(db)
        grade_data = AssignmentGrade(
            totalmarks=totalmarks, obtmarks=obtmarks, comment=comment)
        assignment_service.grade_assignment(assignment_id, grade_data)
        return RedirectResponse(url="/teacher/submissions?graded=true", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/teacher/submissions?error={str(e)}", status_code=303)


@router.post("/delete-all-assignments")
async def delete_all_form(
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignment_service.delete_all_assignments_by_course(current_user.Course)
    return RedirectResponse(url="/teacher/submissions?deleted_all=true", status_code=303)


# ── JSON API endpoints ─────────────────────────────────────────────────────────

@router.post("/api/assignments/questions", response_model=AssignmentQuestionResponse, status_code=201)
async def upload_question_api(
    file: UploadFile = File(...),
    plagiarism_threshold: float = Form(40.0),
    include_references: bool = Form(True),
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    return await assignment_service.upload_question_file(
        file, current_user.Course, plagiarism_threshold, include_references
    )


@router.post("/api/assignments/{assignment_id}/check-plagiarism", response_model=PlagiarismReportResponse)
async def check_plagiarism_api(
    assignment_id: int,
    check_request: PlagiarismCheckRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    plagiarism_service = PlagiarismService(db)
    return plagiarism_service.check_plagiarism(
        assignment_id, check_request.exclude_references, check_request.exclude_quotes
    )


@router.get("/api/submissions", response_model=AssignmentListResponse)
async def get_submissions_api(
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignments = assignment_service.get_assignments_by_course(
        current_user.Course)
    return {"assignments": assignments, "total": len(assignments)}


@router.post("/api/assignments/{assignment_id}/grade", response_model=MessageResponse)
async def grade_api(
    assignment_id: int,
    grade_data: AssignmentGrade,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    assignment_service = AssignmentService(db)
    assignment_service.grade_assignment(assignment_id, grade_data)
    return {"message": "Assignment graded successfully"}


@router.get("/api/assignments/{assignment_id}/plagiarism-report", response_model=PlagiarismReportResponse)
async def get_plagiarism_report_api(
    assignment_id: int,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    plagiarism_service = PlagiarismService(db)
    report = plagiarism_service.get_report(assignment_id)
    if not report:
        raise NotFoundError(detail="Plagiarism report not found")
    return report
