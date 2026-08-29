from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Necessity(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNSTATED = "unstated"


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    necessity: Necessity


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posting: str = Field(min_length=50, max_length=8_000)


class ExtractionToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = None
    company: str | None = None
    requirements: list[Requirement] = Field(min_length=1)


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = None
    company: str | None = None
    requirements: list[Requirement] = Field(min_length=1)
    dropped_count: int = Field(ge=0)
