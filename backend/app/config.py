from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/analyzer.db"
    llama_server_url: str = "http://127.0.0.1:8080"
    llama_context_size: int = 2048
    llama_threads: int = 2
    llm_timeout_seconds: float = 90.0
    max_upload_bytes: int = 25 * 1024 * 1024
    log_token_budget: int = 1100
    max_output_tokens: int = 398

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
