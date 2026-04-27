from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    screenshot_dir: str = "/app/screenshots"
    cors_origin: str = "http://localhost:3000"

    max_pages_to_crawl: int = 5
    max_test_cases: int = 15
    max_reflect_iterations: int = 2
    test_timeout_ms: int = 10_000
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_models: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
