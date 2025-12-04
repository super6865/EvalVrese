"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "EvalVerse"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/evaluation_platform"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://frp-six.com:54940"]
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LLM Configuration
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gpt-4"
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

