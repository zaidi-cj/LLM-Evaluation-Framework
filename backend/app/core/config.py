import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "LLM Evaluation Framework"
    DEBUG: bool = True
    
    # Database configuration: defaults to PostgreSQL but falls back to local SQLite for development
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/llm_eval"
    
    # API Keys for LLM Providers
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Sandbox Database URL for SQL Evaluation (default to separate SQLite memory/file database)
    SQL_SANDBOX_DB_URL: str = "sqlite:///:memory:"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure we use SQLite local fallback if specified or if postgres credentials aren't ready
# (useful for standalone local development testing)
if not settings.DATABASE_URL.startswith("postgresql") and not settings.DATABASE_URL.startswith("sqlite"):
    settings.DATABASE_URL = "sqlite:///./llm_eval.db"

# Force stable v1 API version to bypass beta version deprecations globally for Gemini calls
os.environ["GEMINI_API_VERSION"] = "v1"

# Write keys back to os.environ so that LiteLLM and Ragas can find them globally
if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
    # Ragas and Google AI Studio sometimes look for GOOGLE_API_KEY instead
    os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

if settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
