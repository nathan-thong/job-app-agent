from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.agents.extraction import (
    ExtractionError,
    _read_sample_posting,
    extract,
    validate_mock_fixture,
)
from app.agents.gap_analysis import (
    GapAnalysisError,
    analyze as analyze_gap,
    validate_mock_fixture as validate_gap_fixture,
)
from app.agents.draft import DraftError, draft as create_draft
from app.agents.critique import CritiqueError, critique as run_critique
from app.config import settings
from app.models.config import ConfigResponse, HealthResponse
from app.models.extraction import ExtractionRequest, ExtractionResponse
from app.models.gap_analysis import GapAnalysisRequest, GapAnalysisResponse
from app.models.draft import DraftRequest, DraftResponse
from app.models.critique import CritiqueResponse
from app.models.critique_request import CritiqueRequest
from app.profile import load_profile
from app.rate_limit import SharedRateLimiter, enforce_rate_limit

app = FastAPI(title="Job App Agent")

app.state.profile = load_profile()
app.state.sample_posting = None
if settings.mock_mode:
    validate_mock_fixture()
    app.state.sample_posting = _read_sample_posting()
    extraction = extract(ExtractionRequest(posting=app.state.sample_posting))
    validate_gap_fixture(app.state.profile, GapAnalysisRequest(extraction=extraction))
app.state.rate_limiter = SharedRateLimiter(settings.rate_limit)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return ConfigResponse(
        mock_mode=settings.mock_mode,
        sample_posting=app.state.sample_posting,
        profile_name=app.state.profile.name,
    )


@app.post(
    "/extract",
    response_model=ExtractionResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
def extraction(extraction_request: ExtractionRequest, request: Request) -> ExtractionResponse:
    try:
        return extract(extraction_request, request_id=request.state.request_id)
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail="Extraction could not be completed.") from exc


@app.post(
    "/gap-analysis",
    response_model=GapAnalysisResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
def gap_analysis(
    gap_request: GapAnalysisRequest, request: Request
) -> GapAnalysisResponse:
    try:
        return analyze_gap(gap_request, app.state.profile, request_id=request.state.request_id)
    except GapAnalysisError as exc:
        raise HTTPException(status_code=502, detail="Gap Analysis could not be completed.") from exc


@app.post(
    "/draft",
    response_model=DraftResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
def draft(draft_request: DraftRequest, request: Request) -> DraftResponse:
    try:
        return create_draft(draft_request, app.state.profile, request_id=request.state.request_id)
    except DraftError as exc:
        raise HTTPException(status_code=502, detail="Draft could not be completed.") from exc


@app.post(
    "/critique",
    response_model=CritiqueResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
def critique(critique_request: CritiqueRequest, request: Request) -> CritiqueResponse:
    try:
        return run_critique(critique_request, request_id=request.state.request_id)
    except CritiqueError as exc:
        raise HTTPException(status_code=502, detail="Critique could not be completed.") from exc
