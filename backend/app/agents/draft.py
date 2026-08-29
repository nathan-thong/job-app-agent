import hashlib
import json
import logging
from pathlib import Path

from app.config import settings
from app.llm.client import StructuredCallError, StructuredToolClient
from app.models.critique import CritiqueFinding, FindingSeverity
from app.models.draft import (
    DraftParagraph,
    DraftParagraphToolOutput,
    DraftRequest,
    DraftResponse,
    DraftToolOutput,
)
from app.models.extraction import Requirement
from app.models.gap_analysis import AssessmentOutcome, ProfileEvidence
from app.models.profile import Profile


DRAFT_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "draft.json"
logger = logging.getLogger(__name__)


class DraftError(Exception):
    """A recoverable failure while producing a Draft response."""


def _requirement_key(requirement: Requirement) -> tuple[str, str]:
    return requirement.text, requirement.necessity.value


def _evidence_key(evidence: ProfileEvidence) -> tuple[str, str]:
    return evidence.text, evidence.source.value


def _log_drop(reason: str, text: str, request_id: str) -> None:
    logger.info(
        "draft_provenance_dropped",
        extra={
            "stage": "draft",
            "reason": reason,
            "request_id": request_id,
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    )


def _allowed_provenance(request: DraftRequest) -> dict[tuple[str, str], set[tuple[str, str]]]:
    allowed: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for assessment in request.gap_analysis.assessments:
        if assessment.outcome is not AssessmentOutcome.GAP:
            allowed[_requirement_key(assessment.requirement)] = {
                _evidence_key(item) for item in assessment.evidence
            }
    return allowed


def normalize_draft_output(
    request: DraftRequest,
    output: DraftToolOutput,
    profile: Profile,
    request_id: str = "",
) -> DraftResponse:
    allowed_provenance = _allowed_provenance(request)
    extraction_requirements = {
        _requirement_key(requirement) for requirement in request.extraction.requirements
    }
    dropped_requirement_count = 0
    dropped_evidence_count = 0
    paragraphs: list[DraftParagraph] = []

    for paragraph in output.paragraphs:
        requirements: list[Requirement] = []
        for requirement in paragraph.requirements:
            key = _requirement_key(requirement)
            if key not in extraction_requirements:
                dropped_requirement_count += 1
                _log_drop("unknown_requirement", requirement.text, request_id)
            elif key not in allowed_provenance:
                dropped_requirement_count += 1
                _log_drop("gap_requirement", requirement.text, request_id)
            else:
                requirements.append(requirement)

        allowed_evidence = {
            evidence_key
            for requirement in requirements
            for evidence_key in allowed_provenance[_requirement_key(requirement)]
        }
        evidence: list[ProfileEvidence] = []
        for item in paragraph.evidence:
            if _evidence_key(item) in allowed_evidence:
                evidence.append(item)
            else:
                dropped_evidence_count += 1
                _log_drop("unapproved_evidence", item.text, request_id)

        paragraphs.append(
            DraftParagraph(
                prose=paragraph.prose,
                requirements=requirements,
                evidence=evidence,
            )
        )

    return DraftResponse(
        salutation="Dear Hiring Manager,",
        paragraphs=paragraphs,
        sign_off="Sincerely,",
        candidate_name=profile.name,
        dropped_evidence_count=dropped_evidence_count,
        dropped_requirement_count=dropped_requirement_count,
    )


def _read_fixture(path: Path = DRAFT_FIXTURE_PATH) -> DraftToolOutput:
    try:
        with path.open(encoding="utf-8") as fixture_file:
            return DraftToolOutput.model_validate(json.load(fixture_file))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise DraftError("The Draft fixture is invalid.") from exc


def _prompts(request: DraftRequest, profile: Profile) -> tuple[str, str]:
    system_prompt = (
        "You are the Draft stage of a grounded Cover Letter pipeline. "
        "Write three or four short plain-text paragraphs using only Profile Evidence "
        "approved by Match or Adjacent Requirement Assessments. Never present Adjacent evidence as a Match."
    )
    context = {
        "extraction": request.extraction.model_dump(mode="json"),
        "gap_analysis": request.gap_analysis.model_dump(mode="json"),
        "profile": profile.model_dump(mode="json"),
    }
    if request.previous_cover_letter is not None:
        findings = sorted(
            request.findings or [],
            key=lambda finding: finding.severity is not FindingSeverity.BLOCKING,
        )
        context["previous_cover_letter"] = request.previous_cover_letter.model_dump(mode="json")
        context["findings"] = [finding.model_dump(mode="json") for finding in findings]
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    user_prompt = f"""Instructions:
- Return a complete replacement structured Cover Letter using the provided tool.
- Return exactly three or four non-empty paragraph objects.
- Each factual paragraph must list the Requirements it addresses and the approved Profile Evidence used.
- Do not include Gaps as claims. Adjacent evidence may be framed as transferable, never as direct satisfaction.
- Target 250–350 words, with no postal address, date, subject line, headings, placeholders, or invented recipient.

<trusted_context>
{context_json}
</trusted_context>

Task: Draft the grounded Cover Letter now. """
    return system_prompt, user_prompt


def _provider_output(request: DraftRequest, profile: Profile, request_id: str) -> DraftToolOutput:
    if settings.mock_mode:
        return _read_fixture()

    if not settings.anthropic_api_key:
        raise DraftError("Live mode requires an Anthropic API key.")

    system_prompt, user_prompt = _prompts(request, profile)
    client = StructuredToolClient(api_key=settings.anthropic_api_key, model_name=settings.model_name)
    try:
        return client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=DraftToolOutput,
            parser=DraftToolOutput.model_validate,
            max_tokens=2_048,
        )
    except StructuredCallError as exc:
        raise DraftError("Draft could not be completed.") from exc


def draft(request: DraftRequest, profile: Profile, request_id: str = "") -> DraftResponse:
    output = _provider_output(request, profile, request_id)
    return normalize_draft_output(request, output, profile, request_id)
