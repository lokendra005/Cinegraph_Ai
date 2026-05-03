from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/cinegraph.db"
    llm_provider: str = "auto"  # auto | anthropic | groq
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.3
    log_level: str = "INFO"
    use_migrations: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    outputs_dir: Path = Path("./outputs")
    data_dir: Path = Path("./data")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.outputs_dir.mkdir(parents=True, exist_ok=True)
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


def cors_origin_list() -> list[str]:
    return [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
