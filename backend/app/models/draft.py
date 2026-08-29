from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.critique import CritiqueFinding
from app.models.extraction import ExtractionResponse, Requirement
from app.models.gap_analysis import GapAnalysisResponse, ProfileEvidence


class DraftParagraphToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prose: str = Field(min_length=1)
    requirements: list[Requirement] = Field(default_factory=list)
    evidence: list[ProfileEvidence] = Field(default_factory=list)


class DraftToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphs: list[DraftParagraphToolOutput] = Field(min_length=3, max_length=4)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: ExtractionResponse
    gap_analysis: GapAnalysisResponse
    previous_cover_letter: DraftResponse | None = None
    findings: list[CritiqueFinding] | None = None

    @model_validator(mode="after")
    def revision_context_is_complete(self):
        if (self.previous_cover_letter is None) != (self.findings is None):
            raise ValueError(
                "previous_cover_letter and findings must be supplied together for a revision"
            )
        return self


class DraftParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prose: str = Field(min_length=1)
    requirements: list[Requirement] = Field(default_factory=list)
    evidence: list[ProfileEvidence] = Field(default_factory=list)


class DraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    salutation: str
    paragraphs: list[DraftParagraph] = Field(min_length=3, max_length=4)
    sign_off: str
    candidate_name: str
    dropped_evidence_count: int = Field(ge=0)
    dropped_requirement_count: int = Field(ge=0)
