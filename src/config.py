"""Application configuration using pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Essential environment-specific settings
    database_url: str = "postgresql://papertrail:papertrail_dev_password@localhost:5432/papertrail"
    secret_key: str = "your-secret-key-here-change-in-production"
    debug: bool = False

    # Hardcoded application settings
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    app_name: str = "PaperTrail"
    app_version: str = "0.1.0"
    rate_limit_per_minute: int = 60
    search_results_limit: int = 50
    rrf_k: int = 60
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Optional Twitter/X Integration
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
