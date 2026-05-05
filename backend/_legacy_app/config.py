from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://biduser:bidpass123@localhost:5432/bid_analysis"

    # 공공데이터포털 API
    data_go_kr_api_key: str = ""

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24시간

    # NAS
    nas_mount_path: str = "./data/"

    # Scheduler
    etl_interval_hours: int = 6

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
