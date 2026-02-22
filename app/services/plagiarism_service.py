"""
Plagiarism detection service.
Implements TF-IDF vectorization and cosine similarity for plagiarism detection.
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Assignment, AssignmentQuestionFile
from app.utils.file_utils import convert_to_text
from app.utils.text_processing import preprocess_document
from app.core.config import settings
from app.core.exceptions import PlagiarismCheckError

logger = logging.getLogger(__name__)


class PlagiarismService:
    """Service for detecting plagiarism in assignments."""

    def __init__(self, db: Session):
        self.db = db
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3)  # Use unigrams, bigrams, and trigrams
        )

    def check_plagiarism(
        self,
        assignment_id: int,
        exclude_references: bool = False,
        exclude_quotes: bool = False
    ) -> Dict:
        """
        Check plagiarism for a specific assignment against all others in the same course.

        Args:
            assignment_id: ID of the assignment to check
            exclude_references: Whether to exclude references from comparison
            exclude_quotes: Whether to exclude quotes from comparison

        Returns:
            Dictionary containing plagiarism report

        Raises:
            PlagiarismCheckError: If plagiarism check fails
        """
        try:
            # Get the assignment
            assignment = self.db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()

            if not assignment:
                raise PlagiarismCheckError(detail="Assignment not found")

            # Get plagiarism threshold from assignment question
            question_file = self.db.query(AssignmentQuestionFile).filter(
                AssignmentQuestionFile.course == assignment.course
            ).first()

            threshold = question_file.plagiarism_threshold if question_file else settings.DEFAULT_PLAGIARISM_THRESHOLD

            # Get all other assignments in the same course
            other_assignments = self.db.query(Assignment).filter(
                Assignment.course == assignment.course,
                Assignment.id != assignment_id
            ).all()

            if not other_assignments:
                # No other assignments to compare
                return self._create_empty_report(assignment, threshold)

            # Convert assignment to text
            raw_text = convert_to_text(
                assignment.file_data, assignment.filename)
            target_text = preprocess_document(
                raw_text,
                remove_refs=exclude_references,
                remove_quotes_flag=exclude_quotes
            )

            # Check against other assignments
            matches = self._compare_with_assignments(
                target_text,
                other_assignments,
                exclude_references,
                exclude_quotes
            )

            # Check against external sources using raw text (not stemmed/stripped)
            external_sources = self._check_external_sources(raw_text)

            # Calculate maximum similarity
            max_similarity = max([m['similarity']
                                 for m in matches], default=0.0)

            # Create report
            report = {
                'assignment_id': assignment_id,
                'filename': assignment.filename,
                'plagiarism_percentage': round(max_similarity, 2),
                'matches': matches,
                'external_sources': external_sources,
                'threshold': threshold,
                'passed': max_similarity < threshold,
                'checked_at': datetime.utcnow().isoformat()
            }

            # Auto-grade if threshold exceeded
            if max_similarity >= threshold:
                assignment.obtmarks = 0
                assignment.totalmarks = 100
                assignment.auto_graded = True
                assignment.comment = f"Automatic Grade: 0 (Plagiarism detected: {max_similarity:.2f}%)"

            # Update assignment with report
            assignment.plagiarism_report = report
            assignment.plagiarism_percentage = round(max_similarity, 2)
            assignment.status = "Checked"

            self.db.commit()

            return report

        except Exception as e:
            logger.error(
                f"Plagiarism check failed for assignment {assignment_id}: {str(e)}")
            self.db.rollback()
            raise PlagiarismCheckError(detail=str(e))

    def _compare_with_assignments(
        self,
        target_text: str,
        assignments: List[Assignment],
        exclude_references: bool,
        exclude_quotes: bool
    ) -> List[Dict]:
        """
        Compare target text with other assignments using TF-IDF and cosine similarity.

        Args:
            target_text: Preprocessed text of target assignment
            assignments: List of assignments to compare against
            exclude_references: Whether references were excluded
            exclude_quotes: Whether quotes were excluded

        Returns:
            List of match dictionaries with similarity scores
        """
        matches = []

        # Prepare all documents for vectorization
        documents = [target_text]
        assignment_map = {}

        for idx, assignment in enumerate(assignments, start=1):
            try:
                text = convert_to_text(
                    assignment.file_data, assignment.filename)
                text = preprocess_document(
                    text,
                    remove_refs=exclude_references,
                    remove_quotes_flag=exclude_quotes
                )
                documents.append(text)
                assignment_map[idx] = assignment
            except Exception as e:
                logger.warning(
                    f"Failed to process assignment {assignment.id}: {str(e)}")
                continue

        if len(documents) <= 1:
            return matches

        try:
            # Create TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(documents)

            # Calculate cosine similarity
            similarities = cosine_similarity(
                tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

            # Create match objects
            for idx, similarity in enumerate(similarities, start=1):
                if idx in assignment_map:
                    assignment = assignment_map[idx]
                    similarity_percentage = float(similarity * 100)

                    if similarity_percentage > 5:  # Only include significant matches
                        matches.append({
                            'assignment_id': assignment.id,
                            'filename': assignment.filename,
                            'user_name': f"{assignment.user.Fname} {assignment.user.Lname or ''}".strip(),
                            'similarity': round(similarity_percentage, 2)
                        })

            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x['similarity'], reverse=True)

        except Exception as e:
            logger.error(f"TF-IDF comparison failed: {str(e)}")
            # Fall back to simple comparison if TF-IDF fails
            return self._fallback_comparison(target_text, assignments)

        return matches

    def _fallback_comparison(
        self,
        target_text: str,
        assignments: List[Assignment]
    ) -> List[Dict]:
        """
        Fallback to Jaccard similarity if TF-IDF fails.

        Args:
            target_text: Preprocessed text of target assignment
            assignments: List of assignments to compare against

        Returns:
            List of match dictionaries with similarity scores
        """
        from app.utils.text_processing import get_word_set

        matches = []
        target_words = get_word_set(target_text)

        for assignment in assignments:
            try:
                text = convert_to_text(
                    assignment.file_data, assignment.filename)
                text = preprocess_document(text)
                words = get_word_set(text)

                # Jaccard similarity
                intersection = len(target_words & words)
                union = len(target_words | words)

                if union > 0:
                    similarity = (intersection / union) * 100

                    if similarity > 5:
                        matches.append({
                            'assignment_id': assignment.id,
                            'filename': assignment.filename,
                            'user_name': f"{assignment.user.Fname} {assignment.user.Lname or ''}".strip(),
                            'similarity': round(similarity, 2)
                        })
            except Exception as e:
                logger.warning(
                    f"Fallback comparison failed for assignment {assignment.id}: {str(e)}")
                continue

        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches

    def _check_external_sources(self, text: str) -> List[Dict]:
        """
        Check for external plagiarism sources using Google search.

        Args:
            text: Text to check

        Returns:
            List of up to 5 external sources with title, url, and snippet.
        """
        external_sources = []

        try:
            from googlesearch import search
            from http.client import RemoteDisconnected

            results = list(search(text, num_results=5,
                           advanced=True, sleep_interval=1))

            print(f"Google search results for query: '{text}' - {results}")
            for r in results:

                external_sources.append({
                    'url': r.url,
                    'title': r.title or r.url,
                    'snippet': (r.description or '')[:220]
                })

        except RemoteDisconnected:
            logger.warning(
                "Google search: remote disconnected — no external results returned")
        except Exception as e:
            logger.warning(f"External source check failed: {str(e)}")

        return external_sources

    def _create_empty_report(self, assignment: Assignment, threshold: float) -> Dict:
        """
        Create an empty plagiarism report when there are no comparisons.

        Args:
            assignment: Assignment object
            threshold: Plagiarism threshold

        Returns:
            Empty report dictionary
        """
        report = {
            'assignment_id': assignment.id,
            'filename': assignment.filename,
            'plagiarism_percentage': 0.0,
            'matches': [],
            'external_sources': [],
            'threshold': threshold,
            'passed': True,
            'checked_at': datetime.utcnow().isoformat()
        }

        # Update assignment
        assignment.plagiarism_report = report
        assignment.plagiarism_percentage = 0.0
        assignment.status = "Checked"
        self.db.commit()

        return report

    def get_report(self, assignment_id: int) -> Optional[Dict]:
        """
        Get existing plagiarism report for an assignment.

        Args:
            assignment_id: ID of the assignment

        Returns:
            Plagiarism report dictionary or None if not checked
        """
        assignment = self.db.query(Assignment).filter(
            Assignment.id == assignment_id
        ).first()

        if assignment and assignment.plagiarism_report:
            return assignment.plagiarism_report

        return None
