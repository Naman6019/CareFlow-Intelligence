from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_PATH = Path(__file__).resolve()
PROJECT_ROOT = (
    CONFIG_PATH.parents[3]
    if len(CONFIG_PATH.parents) > 3
    else Path("/")
)


class Settings(BaseSettings):
    app_name: str = "CareFlow Intelligence API"
    app_version: str = "0.5.0"
    data_mode: str = "synthetic"
    database_url: str = (
        "postgresql+asyncpg://careflow:careflow@localhost:5432/careflow"
    )
    api_cors_origins: str = "http://localhost:3000"
    data_dir: Path = PROJECT_ROOT / "data"
    agent_max_download_bytes: int = 50 * 1024 * 1024
    agent_max_extracted_bytes: int = 250 * 1024 * 1024
    document_max_upload_bytes: int = 10 * 1024 * 1024
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    openrouter_timeout_seconds: float = 75.0
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_title: str = "CareFlow Intelligence"
    agent_max_iterations: int = 4
    agent_max_tool_calls: int = 3
    synthea_sample_url: str = (
        "https://synthetichealth.github.io/synthea-sample-data/"
        "downloads/latest/synthea_sample_data_csv_latest.zip"
    )

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.api_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def openrouter_enabled(self) -> bool:
        return bool(self.openrouter_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
