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
    enable_nightly_batch: bool = Field(
        False,
        validation_alias="ENABLE_NIGHTLY_BATCH",
    )
    nightly_batch_hour: int = Field(2, validation_alias="NIGHTLY_BATCH_HOUR")
    nightly_batch_minute: int = Field(0, validation_alias="NIGHTLY_BATCH_MINUTE")
    local_drive_resume_dir: str = Field(
        "data/drive_resumes",
        validation_alias="LOCAL_DRIVE_RESUME_DIR",
    )
    resume_storage_provider: str = Field(
        "local",
        validation_alias="RESUME_STORAGE_PROVIDER",
    )
    resume_storage_providers: str | None = Field(
        None,
        validation_alias="RESUME_STORAGE_PROVIDERS",
    )
    google_drive_folder_id: str = Field(
        "",
        validation_alias="GOOGLE_DRIVE_FOLDER_ID",
    )
    google_service_account_file: str = Field(
        "",
        validation_alias="GOOGLE_SERVICE_ACCOUNT_FILE",
    )
    google_drive_allowed_mime_types: str = Field(
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain",
        validation_alias="GOOGLE_DRIVE_ALLOWED_MIME_TYPES",
    )
    cors_allowed_origins: str = Field(
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    skill_catalog: str = Field(
        "Python,FastAPI,Docker,LLM,LangChain,SQL,PostgreSQL,AWS,Azure,GCP,"
        "Machine Learning,Data Engineering,JavaScript,TypeScript,React",
        validation_alias="SKILL_CATALOG",
    )

    @property
    def cors_allowed_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def resume_storage_provider_list(self) -> list[str]:
        configured_providers = (
            self.resume_storage_providers
            if self.resume_storage_providers is not None
            else self.resume_storage_provider
        )
        return [
            provider.strip().lower()
            for provider in configured_providers.split(",")
            if provider.strip()
        ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
