"""Application configuration using pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "sqlite:///./data/papertrail.db"

    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Embedding Model
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"

    # Application
    app_name: str = "PaperTrail"
    app_version: str = "0.1.0"
    debug: bool = False

    # Twitter/X Integration (optional)
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Search Configuration
    search_results_limit: int = 50
    rrf_k: int = 60

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
