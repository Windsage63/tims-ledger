from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Windsage Ledger"
    app_version: str = "0.1.0"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8004
    database_url: str = "sqlite:///./app-data/windsage-ledger.sqlite3"
    file_storage: str = "./app-data/files"
    cors_allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    cors_allowed_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WINDSAGE_",
        extra="ignore",
    )


settings = Settings()
