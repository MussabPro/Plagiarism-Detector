"""
Assignment service for assignment management operations.
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.db.models import Assignment, AssignmentQuestionFile, AssignmentDueDate, User, AssignmentStatus
from app.db.schemas import AssignmentGrade
from app.utils.file_utils import process_upload
from app.core.exceptions import NotFoundError, ValidationError, FileUploadError
from app.core.config import settings

logger = logging.getLogger(__name__)


class AssignmentService:
    """Service for assignment-related operations."""

    def __init__(self, db: Session):
        self.db = db

    # Assignment Question File Operations

    async def upload_question_file(
        self,
        file: UploadFile,
        course: str,
        plagiarism_threshold: float = 40.0,
        include_references: bool = True
    ) -> AssignmentQuestionFile:
        """
        Upload assignment question file.

        Args:
            file: Uploaded file
            course: Course code
            plagiarism_threshold: Plagiarism detection threshold
            include_references: Whether to include references in detection

        Returns:
            Created AssignmentQuestionFile object

        Raises:
            FileUploadError: If file upload fails
        """
        # Process file upload
        file_data, filename = await process_upload(file)

        try:
            # Delete old question file for this course if exists
            old_file = self.db.query(AssignmentQuestionFile).filter(
                AssignmentQuestionFile.course == course
            ).first()

            if old_file:
                self.db.delete(old_file)

            # Create new question file
            question_file = AssignmentQuestionFile(
                filename=filename,
                file_data=file_data,
                course=course,
                plagiarism_threshold=plagiarism_threshold,
                include_references=include_references
            )

            self.db.add(question_file)
            self.db.commit()
            self.db.refresh(question_file)

            logger.info(
                f"Question file uploaded for course {course}: {filename}")
            return question_file

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upload question file: {str(e)}")
            raise FileUploadError(detail=str(e))

    def get_question_file_by_course(self, course: str) -> Optional[AssignmentQuestionFile]:
        """
        Get assignment question file for a course.

        Args:
            course: Course code

        Returns:
            AssignmentQuestionFile object or None
        """
        return self.db.query(AssignmentQuestionFile).filter(
            AssignmentQuestionFile.course == course
        ).first()

    def get_question_file_by_id(self, file_id: int) -> Optional[AssignmentQuestionFile]:
        """
        Get assignment question file by ID.

        Args:
            file_id: Question file ID

        Returns:
            AssignmentQuestionFile object or None
        """
        return self.db.query(AssignmentQuestionFile).filter(
            AssignmentQuestionFile.id == file_id
        ).first()

    # Assignment Submission Operations

    async def submit_assignment(
        self,
        file: UploadFile,
        user_id: int,
        course: str
    ) -> Assignment:
        """
        Submit student assignment.

        Args:
            file: Uploaded assignment file
            user_id: Student user ID
            course: Course code

        Returns:
            Created Assignment object

        Raises:
            FileUploadError: If file upload fails
            ValidationError: If due date has passed
        """
        # Check due date
        due_date = self.get_due_date(course)
        if due_date and due_date.due_date:
            if datetime.utcnow() > due_date.due_date.replace(tzinfo=None):
                raise ValidationError(detail="Assignment due date has passed")

        # Process file upload
        file_data, filename = await process_upload(file)

        try:
            # Create assignment
            assignment = Assignment(
                filename=filename,
                file_data=file_data,
                user_id=user_id,
                course=course,
                status=AssignmentStatus.NOT_CHECKED
            )

            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(assignment)

            logger.info(f"Assignment submitted by user {user_id}: {filename}")
            return assignment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit assignment: {str(e)}")
            raise FileUploadError(detail=str(e))

    def get_assignment_by_id(self, assignment_id: int) -> Optional[Assignment]:
        """
        Get assignment by ID.

        Args:
            assignment_id: Assignment ID

        Returns:
            Assignment object or None
        """
        return self.db.query(Assignment).filter(Assignment.id == assignment_id).first()

    def get_assignments_by_user(self, user_id: int) -> List[Assignment]:
        """
        Get all assignments by user.

        Args:
            user_id: User ID

        Returns:
            List of Assignment objects
        """
        return self.db.query(Assignment).filter(
            Assignment.user_id == user_id
        ).order_by(Assignment.timeuploaded.desc()).all()

    def get_assignments_by_course(self, course: str) -> List[Assignment]:
        """
        Get all assignments for a course.

        Args:
            course: Course code

        Returns:
            List of Assignment objects
        """
        return self.db.query(Assignment).filter(
            Assignment.course == course
        ).order_by(Assignment.timeuploaded.desc()).all()

    def get_assignments_by_course_and_status(
        self,
        course: str,
        status: AssignmentStatus
    ) -> List[Assignment]:
        """
        Get assignments by course and status.

        Args:
            course: Course code
            status: Assignment status

        Returns:
            List of Assignment objects
        """
        return self.db.query(Assignment).filter(
            Assignment.course == course,
            Assignment.status == status
        ).order_by(Assignment.timeuploaded.desc()).all()

    def grade_assignment(
        self,
        assignment_id: int,
        grade_data: AssignmentGrade
    ) -> Assignment:
        """
        Grade an assignment.

        Args:
            assignment_id: Assignment ID
            grade_data: Grading data

        Returns:
            Updated Assignment object

        Raises:
            NotFoundError: If assignment not found
        """
        assignment = self.get_assignment_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(
                detail=f"Assignment with ID {assignment_id} not found")

        try:
            assignment.totalmarks = grade_data.totalmarks
            assignment.obtmarks = grade_data.obtmarks
            assignment.comment = grade_data.comment
            assignment.status = AssignmentStatus.CHECKED
            assignment.auto_graded = False  # Manual grading

            self.db.commit()
            self.db.refresh(assignment)

            logger.info(f"Assignment graded: {assignment_id}")
            return assignment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to grade assignment: {str(e)}")
            raise

    def delete_assignment(self, assignment_id: int) -> bool:
        """
        Delete an assignment.

        Args:
            assignment_id: Assignment ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If assignment not found
        """
        assignment = self.get_assignment_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(
                detail=f"Assignment with ID {assignment_id} not found")

        try:
            self.db.delete(assignment)
            self.db.commit()
            logger.info(f"Assignment deleted: {assignment_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete assignment: {str(e)}")
            raise

    def delete_all_assignments_by_course(self, course: str) -> int:
        """
        Delete all assignments for a course.

        Args:
            course: Course code

        Returns:
            Number of assignments deleted
        """
        try:
            count = self.db.query(Assignment).filter(
                Assignment.course == course
            ).delete()

            self.db.commit()
            logger.info(f"Deleted {count} assignments for course {course}")
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete assignments: {str(e)}")
            raise

    # Due Date Operations

    def set_due_date(self, course: str, due_date: Optional[datetime]) -> AssignmentDueDate:
        """
        Set or update due date for a course.

        Args:
            course: Course code
            due_date: Due date (None to remove)

        Returns:
            AssignmentDueDate object
        """
        try:
            existing = self.db.query(AssignmentDueDate).filter(
                AssignmentDueDate.course == course
            ).first()

            if existing:
                existing.due_date = due_date
                self.db.commit()
                self.db.refresh(existing)
                logger.info(f"Due date updated for course {course}")
                return existing
            else:
                due_date_obj = AssignmentDueDate(
                    course=course,
                    due_date=due_date
                )
                self.db.add(due_date_obj)
                self.db.commit()
                self.db.refresh(due_date_obj)
                logger.info(f"Due date set for course {course}")
                return due_date_obj

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set due date: {str(e)}")
            raise

    def get_due_date(self, course: str) -> Optional[AssignmentDueDate]:
        """
        Get due date for a course.

        Args:
            course: Course code

        Returns:
            AssignmentDueDate object or None
        """
        return self.db.query(AssignmentDueDate).filter(
            AssignmentDueDate.course == course
        ).first()

    def is_due_date_passed(self, course: str) -> bool:
        """
        Check if due date has passed for a course.

        Args:
            course: Course code

        Returns:
            True if due date has passed, False otherwise
        """
        due_date = self.get_due_date(course)
        if not due_date or not due_date.due_date:
            return False

        return datetime.utcnow() > due_date.due_date.replace(tzinfo=None)

    def count_assignments_by_course(self, course: str) -> int:
        """
        Get count of assignments for a course.

        Args:
            course: Course code

        Returns:
            Number of assignments
        """
        return self.db.query(Assignment).filter(Assignment.course == course).count()

    def count_checked_assignments_by_course(self, course: str) -> int:
        """
        Get count of checked assignments for a course.

        Args:
            course: Course code

        Returns:
            Number of checked assignments
        """
        return self.db.query(Assignment).filter(
            Assignment.course == course,
            Assignment.status == AssignmentStatus.CHECKED
        ).count()
