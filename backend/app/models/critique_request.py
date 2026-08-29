from pydantic import BaseModel, ConfigDict

from app.models.draft import DraftResponse
from app.models.extraction import ExtractionResponse
from app.models.gap_analysis import GapAnalysisResponse


class CritiqueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: ExtractionResponse
    gap_analysis: GapAnalysisResponse
    cover_letter: DraftResponse
