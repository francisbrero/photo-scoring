from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Find the root .env file (two levels up from this file)
_root_env = Path(__file__).parent.parent.parent.parent / ".env"
_env_files = [".env", ".env.local"]
if _root_env.exists():
    _env_files.insert(0, str(_root_env))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=tuple(_env_files), env_file_encoding="utf-8", extra="ignore"
    )

    # Supabase configuration
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str

    # OpenRouter API for inference
    openrouter_api_key: str

    # Stripe configuration
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_100: str = ""
    stripe_price_id_500: str = ""
    stripe_price_id_2000: str = ""

    # Application settings
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://photo-scoring.spraiandprai.com",
    ]

    # Internal API key for Edge Functions (defaults to service key if not set)
    internal_api_key: str = ""

    @property
    def get_internal_api_key(self) -> str:
        """Get the internal API key for Edge Function authentication."""
        return self.internal_api_key or self.supabase_service_key

    @property
    def supabase_anon_key(self) -> str:
        """For client-side operations that don't need service key."""
        return self.supabase_service_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
