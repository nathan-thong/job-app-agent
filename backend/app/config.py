from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    model_name: str = "claude-haiku-4-5"
    mock_mode: bool = True


settings = Settings()
