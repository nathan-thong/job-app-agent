import hashlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path

from app.config import settings
from app.llm.client import StructuredCallError, StructuredToolClient
from app.models.extraction import Requirement
from app.models.gap_analysis import (
    AssessmentOutcome,
    GapAnalysisRequest,
    GapAnalysisResponse,
    GapAnalysisToolOutput,
    ProfileEvidence,
    ProfileEvidenceSource,
    RequirementAssessment,
)
from app.models.profile import Profile
from app.agents.extraction import _normalize_for_source_check


GAP_ANALYSIS_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gap_analysis.json"
logger = logging.getLogger(__name__)


class GapAnalysisError(Exception):
    """A recoverable failure while producing a Gap Analysis response."""


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _profile_section_values(profile: Profile, source: ProfileEvidenceSource) -> Iterable[str]:
    if source is ProfileEvidenceSource.SUMMARY:
        return [profile.summary]
    if source is ProfileEvidenceSource.SKILLS:
        return profile.skills
    if source is ProfileEvidenceSource.EXPERIENCE:
        values: list[str] = []
        for experience in profile.experience:
            values.extend([experience.title, experience.organization, experience.start_date])
            if experience.end_date:
                values.append(experience.end_date)
            values.extend(experience.highlights)
        return values
    if source is ProfileEvidenceSource.PROJECTS:
        values = []
        for project in profile.projects:
            values.extend([project.name, project.description, *project.technologies])
            if project.link:
                values.append(project.link)
        return values
    return profile.education


def _evidence_is_verifiable(evidence: ProfileEvidence, profile: Profile) -> bool:
    normalized_text = _normalize_for_source_check(evidence.text)
    if not normalized_text:
        return False
    return any(
        normalized_text in _normalize_for_source_check(value)
        for value in _profile_section_values(profile, evidence.source)
    )


def _requirement_key(requirement: Requirement) -> tuple[str, str]:
    return requirement.text, requirement.necessity.value


def _log_rejection(
    *,
    reason: str,
    text: str,
    request_id: str,
    count: int = 1,
) -> None:
    fields: dict[str, object] = {
        "stage": "gap_analysis",
        "reason": reason,
        "request_id": request_id,
        "count": count,
        "content_hash": _content_hash(text),
    }
    if settings.log_llm_content:
        fields["rejected_text"] = text
    logger.info("gap_analysis_item_dropped", extra=fields)


def _normalize_evidence(
    assessment: RequirementAssessment,
    profile: Profile,
    request_id: str,
) -> tuple[RequirementAssessment, int]:
    if assessment.outcome is AssessmentOutcome.GAP:
        for evidence in assessment.evidence:
            _log_rejection(
                reason="evidence_attached_to_gap",
                text=evidence.text,
                request_id=request_id,
            )
        if assessment.evidence:
            return assessment.model_copy(update={"evidence": []}), len(assessment.evidence)
        return assessment, 0

    checked: list[ProfileEvidence] = []
    dropped_count = 0
    for evidence in assessment.evidence:
        if _evidence_is_verifiable(evidence, profile):
            checked.append(evidence)
        else:
            dropped_count += 1
            _log_rejection(
                reason="evidence_not_found_in_profile_section",
                text=evidence.text,
                request_id=request_id,
            )

    if checked:
        return assessment.model_copy(update={"evidence": checked}), dropped_count

    return (
        assessment.model_copy(
            update={
                "outcome": AssessmentOutcome.GAP,
                "reason": "No verifiable Profile Evidence found.",
                "evidence": [],
            }
        ),
        dropped_count,
    )


def normalize_assessments(
    extraction: GapAnalysisRequest,
    output: GapAnalysisToolOutput,
    profile: Profile,
    request_id: str = "",
) -> GapAnalysisResponse:
    """Normalize model coverage, evidence, and order without another model call."""

    expected = {
        _requirement_key(requirement): requirement for requirement in extraction.extraction.requirements
    }
    normalized_by_key: dict[tuple[str, str], RequirementAssessment] = {}
    dropped_evidence_count = 0
    dropped_assessment_count = 0

    for assessment in output.assessments:
        key = _requirement_key(assessment.requirement)
        if key not in expected:
            dropped_assessment_count += 1
            _log_rejection(
                reason="assessment_for_unknown_requirement",
                text=assessment.requirement.text,
                request_id=request_id,
            )
            continue
        if key in normalized_by_key:
            dropped_assessment_count += 1
            _log_rejection(
                reason="duplicate_assessment",
                text=assessment.requirement.text,
                request_id=request_id,
            )
            continue

        normalized, evidence_drops = _normalize_evidence(assessment, profile, request_id)
        normalized_by_key[key] = normalized
        dropped_evidence_count += evidence_drops

    ordered: list[RequirementAssessment] = []
    synthesized_assessment_count = 0
    for requirement in extraction.extraction.requirements:
        key = _requirement_key(requirement)
        assessment = normalized_by_key.get(key)
        if assessment is None:
            synthesized_assessment_count += 1
            assessment = RequirementAssessment(
                requirement=requirement,
                outcome=AssessmentOutcome.GAP,
                reason="No assessment returned",
                evidence=[],
            )
        ordered.append(assessment)

    logger.info(
        "gap_analysis_normalized",
        extra={
            "stage": "gap_analysis",
            "request_id": request_id,
            "dropped_evidence_count": dropped_evidence_count,
            "dropped_assessment_count": dropped_assessment_count,
            "synthesized_assessment_count": synthesized_assessment_count,
        },
    )
    return GapAnalysisResponse(
        assessments=ordered,
        dropped_evidence_count=dropped_evidence_count,
        dropped_assessment_count=dropped_assessment_count,
        synthesized_assessment_count=synthesized_assessment_count,
    )


def _read_fixture(path: Path = GAP_ANALYSIS_FIXTURE_PATH) -> GapAnalysisToolOutput:
    try:
        with path.open(encoding="utf-8") as fixture_file:
            return GapAnalysisToolOutput.model_validate(json.load(fixture_file))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise GapAnalysisError("The Gap Analysis fixture is invalid.") from exc


def validate_mock_fixture(profile: Profile, extraction: GapAnalysisRequest) -> None:
    output = _read_fixture()
    response = normalize_assessments(extraction, output, profile)
    if (
        response.dropped_evidence_count
        or response.dropped_assessment_count
        or response.synthesized_assessment_count
    ):
        raise RuntimeError("The canonical Gap Analysis fixture does not cover the Extraction response.")


def _prompts(extraction: GapAnalysisRequest, profile: Profile) -> tuple[str, str]:
    system_prompt = (
        "You are the Gap Analysis stage of a grounded job application pipeline. "
        "Use only the trusted Profile to assess each embedded Requirement. "
        "Match means direct evidence, Adjacent means transferable but not direct, and Gap means no useful evidence."
    )
    extraction_json = json.dumps(extraction.model_dump(mode="json"), ensure_ascii=False, indent=2)
    profile_json = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2)
    user_prompt = f"""Instructions:
- Return one structured Requirement Assessment for each Requirement in the Extraction.
- Embed each complete Requirement exactly as supplied; do not use indexes or generated IDs.
- Copy Profile Evidence verbatim and name its source section.
- Match and Adjacent require evidence. Gap must have no evidence.
- Keep the interpretive reason separate from Profile Evidence.

<extraction>
{extraction_json}
</extraction>

<profile>
{profile_json}
</profile>

Task: Assess every embedded Requirement against the Profile now. """
    return system_prompt, user_prompt


def _provider_output(
    extraction: GapAnalysisRequest, profile: Profile, request_id: str
) -> GapAnalysisToolOutput:
    if settings.mock_mode:
        return _read_fixture()

    if not settings.anthropic_api_key:
        raise GapAnalysisError("Live mode requires an Anthropic API key.")

    system_prompt, user_prompt = _prompts(extraction, profile)
    client = StructuredToolClient(
        api_key=settings.anthropic_api_key,
        model_name=settings.model_name,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    try:
        return client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=GapAnalysisToolOutput,
            parser=GapAnalysisToolOutput.model_validate,
            max_tokens=2_048,
        )
    except StructuredCallError as exc:
        raise GapAnalysisError("Gap Analysis could not be completed.") from exc


def analyze(
    request: GapAnalysisRequest, profile: Profile, request_id: str = ""
) -> GapAnalysisResponse:
    output = _provider_output(request, profile, request_id)
    return normalize_assessments(request, output, profile, request_id)
