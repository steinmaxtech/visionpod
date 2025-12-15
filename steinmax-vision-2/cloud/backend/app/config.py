"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Database
    database_url: str = "postgresql+asyncpg://steinmax:localdev123@localhost:5432/vision"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: str = "steinmax-vision-events"
    
    # Clerk Auth
    clerk_secret_key: Optional[str] = None
    
    # Gatewise
    gatewise_api_url: str = "https://api.gatewise.com/v1"
    gatewise_api_key: Optional[str] = None
    
    # Plate Recognizer
    plate_recognizer_api_key: Optional[str] = None
    
    # App
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
