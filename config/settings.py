"""
Application settings loaded from environment variables.

Uses pydantic-settings for validation. All secrets come from .env file.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys
    gemini_api_key: str = ""
    usajobs_api_key: str = ""
    usajobs_email: str = ""

    # Cache settings
    cache_dir: Path = Path(".cache")
    cache_ttl_hours: int = 6

    # Rate limiting
    default_requests_per_minute: int = 10
    default_burst_size: int = 3

    # Scraper settings
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    playwright_timeout: int = 30000  # ms — timeout for Playwright page loads

    # Gemini classifier
    gemini_model: str = "gemini-3-flash-preview"
    classifier_batch_size: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
