import os
import secrets
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AURA Enterprise SaaS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="", validation_alias="JWT_SECRET")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database URL: uses DATABASE_URL if provided, else falls back to local sqlite database for robust development
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aura.db")
    
    # Private storage directory for evidence items
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "evidence")))
    
    # Allowed CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ALLOW_PRODUCTION_INTEGRATIONS: bool = os.getenv("ALLOW_PRODUCTION_INTEGRATIONS", "false").lower() == "true"

    # Provider credentials must be supplied through deployment environment secrets.
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    DEVICE_GATEWAY_SECRET: Optional[str] = None

    @model_validator(mode="after")
    def configure_development_secret(self):
        if self.SECRET_KEY:
            return self
        if self.ENVIRONMENT.lower() == "production":
            raise ValueError("JWT_SECRET must be configured in production.")
        self.SECRET_KEY = secrets.token_urlsafe(32)
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
