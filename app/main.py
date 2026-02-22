"""
Main FastAPI application entry point.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    ValidationError as CustomValidationError,
    DuplicateError,
    FileUploadError,
    PlagiarismCheckError
)
from app.db.database import init_db, engine, Base
from app.db.models import User, UserRole
from app.core.security import get_password_hash

# Import API routers
from app.api.v1 import auth, admin, teacher, student, common

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Create admin user if doesn't exist
    create_default_admin()

    logger.info(
        f"{settings.APP_NAME} v{settings.VERSION} started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")


def create_default_admin():
    """Create default admin user if it doesn't exist."""
    from sqlalchemy.orm import Session
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(
            User.username == settings.ADMIN_USERNAME).first()

        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                userid=1,
                Fname="Admin",
                Lname="User",
                email="admin@example.com",
                PhoneNo="0000000000",
                Course="ADMIN",
                role=UserRole.ADMIN,
                password=get_password_hash(settings.ADMIN_PASSWORD)
            )
            db.add(admin)
            db.commit()
            logger.info(
                f"Default admin user created: {settings.ADMIN_USERNAME}")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Failed to create admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Plagiarism Detection System with FastAPI",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Add custom filters to Jinja2
templates.env.globals["settings"] = settings


# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors — redirect to login for page requests."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "Authentication failed", "detail": exc.detail}
        )
    return RedirectResponse(url="/login?timeout=true", status_code=302)


@app.exception_handler(PermissionDeniedError)
async def permission_denied_error_handler(request: Request, exc: PermissionDeniedError):
    """Handle permission denied errors — redirect to login for page requests."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "Permission denied", "detail": exc.detail}
        )
    return RedirectResponse(url="/login?error=Access+denied", status_code=302)


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Not found", "detail": exc.detail}
    )


@app.exception_handler(CustomValidationError)
async def validation_error_handler(request: Request, exc: CustomValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Validation error", "detail": exc.detail}
    )


@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    """Handle duplicate resource errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Duplicate resource", "detail": exc.detail}
    )


@app.exception_handler(FileUploadError)
async def file_upload_error_handler(request: Request, exc: FileUploadError):
    """Handle file upload errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "File upload error", "detail": exc.detail}
    )


@app.exception_handler(PlagiarismCheckError)
async def plagiarism_check_error_handler(request: Request, exc: PlagiarismCheckError):
    """Handle plagiarism check errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Plagiarism check error", "detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error",
                 "detail": "An unexpected error occurred"}
    )


# Include API routers
app.include_router(common.router, tags=["Pages"])
app.include_router(auth.router, prefix="/api/v1/auth",
                   tags=["Authentication API"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(teacher.router, prefix="/teacher", tags=["Teacher"])
app.include_router(student.router, prefix="/student", tags=["Student"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
