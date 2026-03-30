from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = "dev-secret"
    cors_origins: str = "http://localhost:3000"
    database_url: str = ""
    database_ssl_insecure: bool = False
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "tabai-audio"
    redis_url: str = "redis://localhost:6379"
    sentry_dsn: str = ""
    max_file_size_mb: int = 100
    free_tier_songs_per_month: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
