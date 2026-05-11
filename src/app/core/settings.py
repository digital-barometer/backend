from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "Digital Barometer API"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    NEWSAPI_API_KEY: str | None = None
    DATAFORSEO_LOGIN: str | None = None
    DATAFORSEO_PASSWORD: str | None = None
    LANGCHAIN_MODEL: str | None = None
    SENTIMENT_MODEL: str | None = None
    ANALYSIS_MODEL: str | None = None
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0, le=2)
    LLM_STRUCTURED_OUTPUT_METHOD: Literal[
        "json_schema",
        "function_calling",
        "json_mode",
    ] = "json_mode"
    LLM_SENTIMENT_BATCH_SIZE: int = Field(default=20, ge=1, le=100)
    LLM_MAX_CONCURRENCY: int = Field(default=3, ge=1, le=20)
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    OUTBOUND_PROXY_URL: str | None = None
    SOURCE_FETCH_MAX_CONCURRENCY: int = Field(default=2, ge=1, le=10)


settings = Settings()
