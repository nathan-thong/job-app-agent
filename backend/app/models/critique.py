from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FindingCode(str, Enum):
    UNSUPPORTED_CLAIM = "unsupported_claim"
    ADJACENT_AS_MATCH = "adjacent_as_match"
    MISSING_ROLE_SPECIFICITY = "missing_role_specificity"
    FORBIDDEN_STRUCTURE = "forbidden_structure"
    INCOHERENT_PROSE = "incoherent_prose"
    WORD_COUNT = "word_count"
    REPETITION = "repetition"
    WEAK_PHRASING = "weak_phrasing"
    GENERIC_TONE = "generic_tone"
    MISSED_OPPORTUNITY = "missed_opportunity"


class FindingSeverity(str, Enum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class CritiqueFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: FindingCode
    severity: FindingSeverity
    paragraph_number: int | None = Field(default=None, ge=1)
    message: str = Field(min_length=1)


class SemanticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: FindingCode
    paragraph_number: int | None = None
    message: str = Field(min_length=1)


class CritiqueToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[SemanticFinding] = Field(default_factory=list)


class CritiqueVerdict(str, Enum):
    PASS = "pass"
    REVISE = "revise"


class CritiqueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[CritiqueFinding] = Field(default_factory=list)
    verdict: CritiqueVerdict
