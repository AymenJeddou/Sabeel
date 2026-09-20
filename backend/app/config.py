"""Shared config (Sprint1_Action_Plan.md, Section 4.6)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/roadscan"
    model_path: str = "models/pothole_model.onnx"
    chroma_db_path: str = "rag-service/chroma_db"
    llm_endpoint: str = ""
    llm_api_key: str = ""
    max_dedup_distance_m: float = 5
    score_threshold_for_sheet: int = 3
    port: int = 8000
    cloud_run_service_name: str = "roadscan-api"


settings = Settings()
