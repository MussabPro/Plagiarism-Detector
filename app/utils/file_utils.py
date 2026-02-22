"""
File handling utilities.
Functions for file conversion, validation, and processing.
"""
from typing import Optional, List
import io
import re
from PyPDF2 import PdfReader
from docx import Document
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import FileUploadError


def validate_file_extension(filename: str) -> bool:
    """
    Validate file extension against allowed extensions.

    Args:
        filename: Name of the file to validate

    Returns:
        True if extension is allowed, False otherwise
    """
    ext = get_file_extension(filename)
    return ext in settings.ALLOWED_EXTENSIONS


def validate_file_size(file_data: bytes) -> bool:
    """
    Validate file size against maximum upload size.

    Args:
        file_data: File content as bytes

    Returns:
        True if size is within limit, False otherwise
    """
    return len(file_data) <= settings.MAX_UPLOAD_SIZE


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Name of the file

    Returns:
        File extension (e.g., '.pdf', '.txt')
    """
    return '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def convert_pdf_to_text(file_data: bytes) -> str:
    """
    Convert PDF file to text.

    Args:
        file_data: PDF file content as bytes

    Returns:
        Extracted text from PDF

    Raises:
        FileUploadError: If PDF conversion fails
    """
    try:
        pdf_file = io.BytesIO(file_data)
        reader = PdfReader(pdf_file)

        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return text.strip()
    except Exception as e:
        raise FileUploadError(detail=f"Failed to convert PDF: {str(e)}")


def convert_docx_to_text(file_data: bytes) -> str:
    """
    Convert DOCX file to text.

    Args:
        file_data: DOCX file content as bytes

    Returns:
        Extracted text from DOCX

    Raises:
        FileUploadError: If DOCX conversion fails
    """
    try:
        docx_file = io.BytesIO(file_data)
        doc = Document(docx_file)

        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

        return text.strip()
    except Exception as e:
        raise FileUploadError(detail=f"Failed to convert DOCX: {str(e)}")


def convert_to_text(file_data: bytes, filename: str) -> str:
    """
    Convert file to text based on its extension.

    Args:
        file_data: File content as bytes
        filename: Name of the file (to determine type)

    Returns:
        Extracted text content

    Raises:
        FileUploadError: If file type is unsupported or conversion fails
    """
    ext = get_file_extension(filename)

    if ext == '.pdf':
        return convert_pdf_to_text(file_data)
    elif ext == '.docx':
        return convert_docx_to_text(file_data)
    elif ext == '.txt':
        try:
            return file_data.decode('utf-8')
        except UnicodeDecodeError:
            # Try other encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    return file_data.decode(encoding)
                except:
                    continue
            raise FileUploadError(detail="Unable to decode text file")
    else:
        raise FileUploadError(detail=f"Unsupported file type: {ext}")


async def process_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Process an uploaded file with validation.

    Args:
        file: Uploaded file object

    Returns:
        Tuple of (file_data, filename)

    Raises:
        FileUploadError: If validation fails
    """
    # Validate extension
    if not validate_file_extension(file.filename):
        allowed = ', '.join(settings.ALLOWED_EXTENSIONS)
        raise FileUploadError(
            detail=f"Invalid file type. Allowed types: {allowed}"
        )

    # Read file data
    file_data = await file.read()

    # Validate size
    if not validate_file_size(file_data):
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise FileUploadError(
            detail=f"File too large. Maximum size: {max_mb}MB"
        )

    # Validate it's not empty
    if len(file_data) == 0:
        raise FileUploadError(detail="File is empty")

    return file_data, file.filename


def validate_magic_bytes(file_data: bytes, filename: str) -> bool:
    """
    Validate file magic bytes match the extension.
    Basic security check to prevent file type spoofing.

    Args:
        file_data: File content as bytes
        filename: Name of the file

    Returns:
        True if magic bytes match extension, False otherwise
    """
    if len(file_data) < 4:
        return False

    ext = get_file_extension(filename)
    magic = file_data[:4]

    # PDF magic bytes
    if ext == '.pdf':
        return file_data[:5] == b'%PDF-'

    # DOCX magic bytes (ZIP format)
    elif ext == '.docx':
        return magic == b'PK\x03\x04'

    # TXT files don't have magic bytes
    elif ext == '.txt':
        return True

    return False
