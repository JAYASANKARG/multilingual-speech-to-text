from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://stt:stt@localhost:5432/stt"
    test_database_url: str = "postgresql+asyncpg://stt:stt@localhost:5432/stt_test"
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-transcribe-live"
    session_salt: str = ""

    max_session_seconds: int = 300
    silence_timeout_seconds: int = 15
    sessions_per_hour: int = 10
    max_concurrent_sessions: int = 3

    static_dir: str = ""

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
