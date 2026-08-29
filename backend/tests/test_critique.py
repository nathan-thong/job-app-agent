import pytest
from fastapi.testclient import TestClient

from app.agents import critique as critique_agent
from app.agents.critique import deterministic_findings, normalize_findings
from app.main import app
from app.models.critique import (
    CritiqueResponse,
    CritiqueToolOutput,
    CritiqueVerdict,
    FindingCode,
    FindingSeverity,
    SemanticFinding,
)
from app.models.critique_request import CritiqueRequest
from app.models.draft import DraftParagraph, DraftResponse
from app.models.extraction import ExtractionResponse, Necessity, Requirement
from app.models.gap_analysis import (
    AssessmentOutcome,
    GapAnalysisResponse,
    RequirementAssessment,
)


REQUIREMENT = Requirement(text="Python", necessity=Necessity.REQUIRED)


def make_request(*paragraphs: str) -> CritiqueRequest:
    cover_letter = DraftResponse(
        salutation="Dear Hiring Manager,",
        paragraphs=[DraftParagraph(prose=paragraph) for paragraph in paragraphs],
        sign_off="Sincerely,",
        candidate_name="Jordan Ellis",
        dropped_evidence_count=0,
        dropped_requirement_count=0,
    )
    return CritiqueRequest(
        extraction=ExtractionResponse(
            job_title="Senior Backend Engineer",
            company="Harbor & Pine",
            requirements=[REQUIREMENT],
            dropped_count=0,
        ),
        gap_analysis=GapAnalysisResponse(
            assessments=[
                RequirementAssessment(
                    requirement=REQUIREMENT,
                    outcome=AssessmentOutcome.GAP,
                    reason="No evidence.",
                    evidence=[],
                )
            ],
            dropped_evidence_count=0,
            dropped_assessment_count=0,
            synthesized_assessment_count=0,
        ),
        cover_letter=cover_letter,
    )


def test_deterministic_word_count_is_advisory():
    findings = deterministic_findings(make_request("One.", "Two.", "Three."))

    assert len(findings) == 1
    assert findings[0].code is FindingCode.WORD_COUNT
    assert findings[0].severity is FindingSeverity.ADVISORY


def test_deterministic_forbidden_structure_is_blocking():
    findings = deterministic_findings(make_request("# Cover Letter", "Body.", "Closing."))

    assert any(finding.code is FindingCode.FORBIDDEN_STRUCTURE for finding in findings)
    assert next(
        finding for finding in findings if finding.code is FindingCode.FORBIDDEN_STRUCTURE
    ).severity is FindingSeverity.BLOCKING


def test_normalize_findings_derives_severity_verdict_and_order():
    result = normalize_findings(
        [
            SemanticFinding(
                code=FindingCode.GENERIC_TONE,
                paragraph_number=1,
                message="Make the tone more specific.",
            ),
            SemanticFinding(
                code=FindingCode.UNSUPPORTED_CLAIM,
                paragraph_number=2,
                message="This claim is not supported.",
            ),
        ],
        [],
        paragraph_count=3,
    )

    assert result.verdict is CritiqueVerdict.REVISE
    assert [finding.severity for finding in result.findings] == [
        FindingSeverity.BLOCKING,
        FindingSeverity.ADVISORY,
    ]


def test_normalize_findings_makes_out_of_range_paragraph_letter_wide_and_deduplicates():
    result = normalize_findings(
        [
            SemanticFinding(
                code=FindingCode.UNSUPPORTED_CLAIM,
                paragraph_number=99,
                message="First message.",
            ),
            SemanticFinding(
                code=FindingCode.UNSUPPORTED_CLAIM,
                paragraph_number=None,
                message="Duplicate message.",
            ),
        ],
        [],
        paragraph_count=3,
    )

    assert len(result.findings) == 1
    assert result.findings[0].paragraph_number is None
    assert result.findings[0].severity is FindingSeverity.BLOCKING


def test_advisory_semantic_finding_can_pass_but_semantic_call_is_still_made(monkeypatch):
    called = False

    def fake_provider(request, request_id):
        nonlocal called
        called = True
        return CritiqueToolOutput(
            findings=[
                SemanticFinding(
                    code=FindingCode.GENERIC_TONE,
                    message="Make the opening more specific.",
                )
            ]
        )

    monkeypatch.setattr(critique_agent, "_provider_output", fake_provider)
    response = critique_agent.critique(make_request("One.", "Two.", "Three."))

    assert called
    assert response.verdict is CritiqueVerdict.PASS
    assert any(finding.code is FindingCode.GENERIC_TONE for finding in response.findings)


def test_semantic_failure_does_not_become_a_pass(monkeypatch):
    def fail_provider(request, request_id):
        raise critique_agent.CritiqueError("semantic failure")

    monkeypatch.setattr(critique_agent, "_provider_output", fail_provider)

    with pytest.raises(critique_agent.CritiqueError):
        critique_agent.critique(make_request("# Heading", "Two.", "Three."))


def test_critique_response_has_no_normalization_counters():
    response = CritiqueResponse(findings=[], verdict=CritiqueVerdict.PASS)

    assert set(response.model_dump()) == {"findings", "verdict"}


def test_critique_endpoint_returns_typed_response():
    with TestClient(app) as client:
        response = client.post("/critique", json=make_request("One.", "Two.", "Three.").model_dump(mode="json"))

    assert response.status_code == 200
    assert set(response.json()) == {"findings", "verdict"}
    assert response.json()["verdict"] == "pass"
