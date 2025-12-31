from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def supabase_anon_key(self) -> str:
        """For client-side operations that don't need service key."""
        return self.supabase_service_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
