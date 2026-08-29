from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.extraction import ExtractionResponse, Requirement


class AssessmentOutcome(str, Enum):
    MATCH = "match"
    ADJACENT = "adjacent"
    GAP = "gap"


class ProfileEvidenceSource(str, Enum):
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"


class ProfileEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    source: ProfileEvidenceSource


class RequirementAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: Requirement
    outcome: AssessmentOutcome
    reason: str = Field(min_length=1)
    evidence: list[ProfileEvidence] = Field(default_factory=list)


class GapAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: ExtractionResponse


class GapAnalysisToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[RequirementAssessment] = Field(default_factory=list)


class GapAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[RequirementAssessment] = Field(min_length=1)
    dropped_evidence_count: int = Field(ge=0)
    dropped_assessment_count: int = Field(ge=0)
    synthesized_assessment_count: int = Field(ge=0)
