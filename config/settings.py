from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kombee_hackathon")
    
    # Individual DB fields (fallback)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "kombee_hackathon"
    db_user: str = "postgres"
    db_password: str = "postgres"
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    
    # Application
    flask_env: str = "development"
    flask_debug: bool = True
    secret_key: str = os.getenv("SECRET_KEY", "default-secret-key")
    port: int = 5000
    
    # Vector Database
    vector_db_path: str = "./vector_store"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore" # Allow extra env vars without error
    )

settings = Settings()