"""
Configuration management for Support Knowledge Claw.
Loads settings from .env file with sensible defaults.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root = parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Agent ---
    confidence_threshold: float = 0.75

    # --- Storage ---
    chroma_persist_dir: str = str(PROJECT_ROOT / "chroma_db")
    database_path: str = str(PROJECT_ROOT / "support_claw.db")

    # --- Paths ---
    knowledge_base_dir: str = str(PROJECT_ROOT / "data" / "knowledge_base")
    frontend_dir: str = str(PROJECT_ROOT / "frontend")


# Singleton instance
settings = Settings()
