from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    model_name: str = "claude-haiku-4-5"
    mock_mode: bool = True
    rate_limit: str = "40/hour"
    log_llm_content: bool = False
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)


settings = Settings()
