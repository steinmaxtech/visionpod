"""
Edge Agent Configuration

All settings are loaded from environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Edge agent settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # =========================================================================
    # DEVICE IDENTITY
    # =========================================================================
    # Get these from your cloud portal when you register the device
    
    device_id: str
    property_id: str
    
    # =========================================================================
    # CLOUD CONNECTION
    # =========================================================================
    # Your backend API URL (via Tailscale or public)
    
    cloud_api_url: str = "http://100.64.0.1:8000/api/v1"
    cloud_api_timeout: int = 10
    cloud_api_key: Optional[str] = None  # Optional API key for auth
    
    # =========================================================================
    # GATEWISE
    # =========================================================================
    # Access control integration
    
    gatewise_api_url: str = "https://api.gatewise.com/v1"
    gatewise_api_key: Optional[str] = None
    gatewise_device_id: Optional[str] = None
    gatewise_enabled: bool = True
    gatewise_timeout: int = 5  # Gate should open fast
    
    # =========================================================================
    # REDIS
    # =========================================================================
    # Local cache for plate lookups
    
    redis_url: str = "redis://localhost:6379/0"
    redis_plate_ttl: int = 86400  # Cache plates for 24 hours
    
    # =========================================================================
    # FRIGATE
    # =========================================================================
    # Video recording integration
    
    frigate_url: str = "http://frigate:5000"
    frigate_enabled: bool = True
    frigate_camera_name: str = "gate_camera"
    
    # =========================================================================
    # SYNC SETTINGS
    # =========================================================================
    # How often to sync with cloud
    
    sync_interval_seconds: int = 60
    heartbeat_interval_seconds: int = 30
    
    # =========================================================================
    # S3 UPLOADS (Optional)
    # =========================================================================
    # Upload event images/clips to S3
    
    s3_enabled: bool = False
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # =========================================================================
    # SERVER SETTINGS
    # =========================================================================
    
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    
    # =========================================================================
    # LOCAL STORAGE
    # =========================================================================
    
    data_dir: str = "/data"
    sqlite_path: str = "/data/fallback.db"


settings = Settings()
