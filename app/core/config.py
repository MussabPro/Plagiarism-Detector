"""
Application configuration using Pydantic BaseSettings.
Loads configuration from environment variables with sensible defaults.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import secrets
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "Plagiarism Detection System"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Admin credentials (can be overridden via environment variables)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"  # Should be changed in production

    # Database — must be set via DATABASE_URL in your .env file
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost:3306/plagcheck"

    # File Upload
    MAX_UPLOAD_SIZE: int = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: set = {".txt", ".pdf", ".docx"}
    UPLOAD_FOLDER: str = "uploads"  # For temporary file processing

    # Plagiarism Detection
    DEFAULT_PLAGIARISM_THRESHOLD: float = 40.0
    MAX_EXTERNAL_SOURCES: int = 3

    # CORS
    CORS_ORIGINS: list = ["*"]  # Configure for production

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is strong enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()
