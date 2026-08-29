import json
import logging
import re
from pathlib import Path

from app.config import settings
from app.llm.client import StructuredCallError, StructuredToolClient
from app.models.critique import (
    CritiqueFinding,
    CritiqueResponse,
    CritiqueToolOutput,
    CritiqueVerdict,
    FindingCode,
    FindingSeverity,
    SemanticFinding,
)
from app.models.critique_request import CritiqueRequest


CRITIQUE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "critique.json"
CRITIQUE_INITIAL_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "critique_initial.json"
logger = logging.getLogger(__name__)

BLOCKING_CODES = frozenset(
    {
        FindingCode.UNSUPPORTED_CLAIM,
        FindingCode.ADJACENT_AS_MATCH,
        FindingCode.MISSING_ROLE_SPECIFICITY,
        FindingCode.FORBIDDEN_STRUCTURE,
        FindingCode.INCOHERENT_PROSE,
    }
)


class CritiqueError(Exception):
    """A recoverable failure while producing a Critique response."""


def _severity_for(code: FindingCode) -> FindingSeverity:
    return FindingSeverity.BLOCKING if code in BLOCKING_CODES else FindingSeverity.ADVISORY


def _letter_text(request: CritiqueRequest) -> str:
    paragraphs = "\n\n".join(paragraph.prose for paragraph in request.cover_letter.paragraphs)
    return "\n\n".join(
        [request.cover_letter.salutation, paragraphs, request.cover_letter.sign_off, request.cover_letter.candidate_name]
    )


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text, flags=re.UNICODE))


def deterministic_findings(request: CritiqueRequest) -> list[CritiqueFinding]:
    findings: list[CritiqueFinding] = []
    count = _word_count(_letter_text(request))
    if count < 250 or count > 350:
        findings.append(
            CritiqueFinding(
                code=FindingCode.WORD_COUNT,
                severity=FindingSeverity.ADVISORY,
                message=f"The Cover Letter is {count} words; the target is 250–350 words.",
            )
        )

    structure_patterns = (
        re.compile(r"(?im)^\s*#{1,6}\s+"),
        re.compile(r"(?im)^\s*(?:subject|re)\s*:"),
        re.compile(r"\[[^\]\r\n]+\]"),
        re.compile(
            r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        ),
        re.compile(
            r"(?im)^\s*\d{1,6}\s+[\w .'-]+\s+"
            r"(?:street|st|road|rd|avenue|ave|drive|dr|boulevard|blvd|lane|ln)\b"
        ),
        re.compile(r"(?im)^\s*dear\s+(?!hiring manager\b).+,?\s*$"),
    )
    if any(pattern.search(_letter_text(request)) for pattern in structure_patterns):
        findings.append(
            CritiqueFinding(
                code=FindingCode.FORBIDDEN_STRUCTURE,
                severity=FindingSeverity.BLOCKING,
                message="Remove address, date, subject, heading, placeholder, or invented recipient structure from the Cover Letter.",
            )
        )
    return findings


def _log_normalization(reason: str, request_id: str) -> None:
    logger.info(
        "critique_finding_normalized",
        extra={"stage": "critique", "reason": reason, "request_id": request_id},
    )


def normalize_findings(
    semantic: list[SemanticFinding],
    deterministic: list[CritiqueFinding],
    paragraph_count: int,
    request_id: str = "",
) -> CritiqueResponse:
    findings = list(deterministic)
    for finding in semantic:
        paragraph_number = finding.paragraph_number
        if paragraph_number is not None and not 1 <= paragraph_number <= paragraph_count:
            _log_normalization("paragraph_number_out_of_range", request_id)
            paragraph_number = None
        findings.append(
            CritiqueFinding(
                code=finding.code,
                severity=_severity_for(finding.code),
                paragraph_number=paragraph_number,
                message=finding.message,
            )
        )

    deduplicated: list[CritiqueFinding] = []
    seen: set[tuple[FindingCode, int | None]] = set()
    for finding in findings:
        key = (finding.code, finding.paragraph_number)
        if key in seen:
            _log_normalization("duplicate_finding", request_id)
            continue
        seen.add(key)
        deduplicated.append(finding)

    deduplicated.sort(key=lambda finding: finding.severity is FindingSeverity.ADVISORY)
    verdict = (
        CritiqueVerdict.REVISE
        if any(finding.severity is FindingSeverity.BLOCKING for finding in deduplicated)
        else CritiqueVerdict.PASS
    )
    return CritiqueResponse(findings=deduplicated, verdict=verdict)


def _read_fixture(path: Path = CRITIQUE_FIXTURE_PATH) -> CritiqueToolOutput:
    try:
        with path.open(encoding="utf-8") as fixture_file:
            return CritiqueToolOutput.model_validate(json.load(fixture_file))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise CritiqueError("The Critique fixture is invalid.") from exc


def _prompts(request: CritiqueRequest) -> tuple[str, str]:
    system_prompt = (
        "You are the Critique stage of a grounded Cover Letter pipeline. "
        "Return only semantic Critique Findings. Identify unsupported or overstated claims, "
        "Adjacent evidence presented as direct, missing role specificity, forbidden structure, "
        "incoherent prose, and advisory writing issues."
    )
    context = json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2)
    user_prompt = f"""Instructions:
- Return Findings only; do not return severity or a verdict.
- Use the supplied one-based paragraph number for paragraph-specific findings, or omit it for letter-wide findings.
- Treat Profile Evidence as provenance, not proof that every sentence is supported.
- Unsupported claims and Adjacent evidence presented as direct Matches are blocking.

<trusted_context>
{context}
</trusted_context>

Task: Critique the complete Cover Letter and return every relevant semantic Finding now. """
    return system_prompt, user_prompt


def _provider_output(request: CritiqueRequest, request_id: str) -> CritiqueToolOutput:
    if settings.mock_mode:
        has_demo_claim = "I have led platform teams" in request.cover_letter.paragraphs[0].prose
        return _read_fixture(CRITIQUE_INITIAL_FIXTURE_PATH if has_demo_claim else CRITIQUE_FIXTURE_PATH)

    if not settings.anthropic_api_key:
        raise CritiqueError("Live mode requires an Anthropic API key.")

    system_prompt, user_prompt = _prompts(request)
    client = StructuredToolClient(api_key=settings.anthropic_api_key, model_name=settings.model_name)
    try:
        return client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=CritiqueToolOutput,
            parser=CritiqueToolOutput.model_validate,
            max_tokens=2_048,
        )
    except StructuredCallError as exc:
        raise CritiqueError("Critique could not be completed.") from exc


def critique(request: CritiqueRequest, request_id: str = "") -> CritiqueResponse:
    deterministic = deterministic_findings(request)
    semantic = _provider_output(request, request_id)
    return normalize_findings(
        semantic.findings,
        deterministic,
        len(request.cover_letter.paragraphs),
        request_id,
    )
