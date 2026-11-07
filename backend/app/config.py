"""Core API settings. Every value can be overridden by an environment variable
of the same name in upper case (see the repo root .env.example)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/roadscan"
    model_path: str = "models/pothole_model.onnx"
    # The RAG service is its own process (own Dockerfile, own deps): the Core
    # API calls it over HTTP and never imports it.
    rag_service_url: str = "http://localhost:8001"
    rag_timeout_s: float = 30

    # Reports and potholes
    max_dedup_distance_m: float = 5
    score_threshold_for_sheet: int = 3
    min_distinct_devices_to_confirm: int = 2
    # Detection gate. 0.28 is the threshold tuned on the validation split
    # (ml-training/models/test_metrics.json, conf_threshold).
    min_confidence: float = 0.28
    max_upload_mb: float = 8
    max_report_age_days: float = 7  # offline queues can hold a report for days
    # A new report this close to a pothole fixed in the last N days counts as "still there".
    reopen_window_days: int = 90

    # Confirmations ("I see it too")
    confirm_radius_m: float = 50
    max_confirm_gps_accuracy_m: float = 40
    reopen_min_devices: int = 2
    not_pothole_min_devices: int = 2

    # Security
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    internal_token: str = ""  # protects /internal/*; empty disables those routes
    rate_limits_enabled: bool = True

    # Photos: "local" (static/photos) or "supabase" (Supabase Storage bucket)
    storage_backend: str = "local"
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "photos"
    blur_faces_and_plates: bool = True

    # Background jobs
    job_max_attempts: int = 5
    # Seconds between worker passes inside the API process; 0 disables the
    # loop (Cloud Run: use the scheduled /internal/run endpoint instead).
    job_loop_interval_s: float = 20

    # OpenStreetMap enrichment
    osm_enabled: bool = True
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osm_user_agent: str = "Sabeel/1.0 (pothole reporting, Tunisia; github.com/AymenJeddou/Sabeel)"
    osm_timeout_s: float = 8
    default_office_code: str = "mun-tunis"

    # Routing and weather (free, no key)
    osrm_url: str = "https://router.project-osrm.org"
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    rain_alert_mm: float = 10

    # Public links printed on PDFs and QR codes
    public_base_url: str = "http://localhost:5173"

    port: int = 8000
    cloud_run_service_name: str = "sabeel-api"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
