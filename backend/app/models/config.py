from pydantic import BaseModel, ConfigDict


class ConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mock_mode: bool
    sample_posting: str | None
    profile_name: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
