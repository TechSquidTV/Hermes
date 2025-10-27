import importlib.metadata
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Settings
    api_title: str = Field(default="Hermes API")
    api_description: str = Field(default="Video downloader API")

    @property
    def api_version(self) -> str:
        """Get version from pyproject.toml or package metadata."""
        # Try to get from installed package metadata first
        try:
            return importlib.metadata.version("hermes-api")
        except importlib.metadata.PackageNotFoundError:
            pass

        # Try to read from pyproject.toml (development)
        try:
            import pathlib

            pyproject_path = (
                pathlib.Path(__file__).parent.parent.parent / "pyproject.toml"
            )
            if pyproject_path.exists():
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Extract version using regex
                match = re.search(
                    r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE
                )
                if match:
                    return match.group(1)
        except (FileNotFoundError, OSError):
            pass

        # Final fallback
        return "1.0.0"

    debug: bool = Field(default=False)

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/hermes.db")
    database_echo: bool = Field(default=False)

    # Redis/Cache
    redis_url: str = Field(default="redis://localhost:6379")
    redis_db: int = Field(default=0)

    # Security
    secret_key: str = Field(
        ...,
        description="JWT secret key for token signing. Must be set via HERMES_SECRET_KEY environment variable.",
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440)  # 24 hours for testing
    refresh_token_expire_days: int = Field(default=30)  # 30 days for testing

    # File Storage
    download_dir: str = Field(default="./downloads")
    temp_dir: str = Field(default="./temp")

    # API Keys
    api_keys: list[str] = Field(default_factory=list)

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60)

    # Security Settings
    enable_token_blacklist: bool = Field(default=True)
    enable_rate_limiting: bool = Field(default=True)
    max_login_attempts: int = Field(default=5)
    login_attempt_window_minutes: int = Field(default=15)

    # CORS Settings
    # Default includes common development ports and example domains
    # In production, override with HERMES_ALLOWED_ORIGINS environment variable
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",  # Production frontend (nginx)
            "http://localhost:5173",  # Development frontend (Vite)
            "https://hermes.example.com",  # Example production domain
            "https://hermes-api.example.com",  # Example separate API domain
        ]
    )
    allow_credentials: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="HERMES_", case_sensitive=False)


# Global settings instance
settings = Settings()
