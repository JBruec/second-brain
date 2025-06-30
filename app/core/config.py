from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Application settings
    app_name: str = "AI Second Brain"
    debug: bool = False
    environment: str = "production"
    
    # Database settings
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "second_brain")
    
    # Memory store settings
    mem0_api_key: Optional[str] = os.getenv("MEM0_API_KEY")
    
    # AI settings
    voyage_api_key: Optional[str] = os.getenv("VOYAGE_API_KEY")
    abacus_api_key: Optional[str] = os.getenv("ABACUS_API_KEY")
    abacus_base_url: str = os.getenv("ABACUS_BASE_URL", "https://api.abacus.ai")
    
    # Security settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    
    # File upload settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Apple integration settings
    apple_script_enabled: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()