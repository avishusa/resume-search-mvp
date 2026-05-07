from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(
        "resume-search-api",
        validation_alias=AliasChoices("APP_NAME", "APP_APP_NAME"),
    )
    resume_parser_provider: str = Field(
        "ollama",
        validation_alias="RESUME_PARSER_PROVIDER",
    )
    ollama_base_url: str = Field(
        "http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field("llama3.1:8b", validation_alias="OLLAMA_MODEL")
    ollama_timeout_seconds: int = Field(
        60,
        validation_alias="OLLAMA_TIMEOUT_SECONDS",
    )
    ollama_max_resume_chars: int = Field(
        12000,
        validation_alias="OLLAMA_MAX_RESUME_CHARS",
    )
    database_url: str = Field(
        "sqlite:///./data/resume_search.db",
        validation_alias="DATABASE_URL",
    )
    skill_catalog: str = Field(
        "Python,FastAPI,Docker,LLM,LangChain,SQL,PostgreSQL,AWS,Azure,GCP,"
        "Machine Learning,Data Engineering,JavaScript,TypeScript,React",
        validation_alias="SKILL_CATALOG",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
