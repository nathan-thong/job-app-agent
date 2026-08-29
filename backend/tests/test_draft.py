import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.critique import critique
from app.agents.draft import draft, normalize_draft_output
from app.models.critique import CritiqueFinding, FindingCode, FindingSeverity
from app.models.critique_request import CritiqueRequest
from app.models.draft import (
    DraftParagraphToolOutput,
    DraftRequest,
    DraftResponse,
    DraftToolOutput,
)
from app.models.extraction import ExtractionResponse, Necessity, Requirement
from app.models.gap_analysis import (
    AssessmentOutcome,
    GapAnalysisResponse,
    ProfileEvidence,
    ProfileEvidenceSource,
    RequirementAssessment,
)
from app.profile import load_profile
from app.main import app


PROFILE = load_profile()


def req(text: str, necessity: Necessity = Necessity.REQUIRED) -> Requirement:
    return Requirement(text=text, necessity=necessity)


def evidence(text: str, source: ProfileEvidenceSource) -> ProfileEvidence:
    return ProfileEvidence(text=text, source=source)


def assessment(
    requirement: Requirement,
    outcome: AssessmentOutcome,
    evidence_items: list[ProfileEvidence] | None = None,
) -> RequirementAssessment:
    return RequirementAssessment(
        requirement=requirement,
        outcome=outcome,
        reason="A grounded assessment.",
        evidence=evidence_items or [],
    )


def request_with_gap(
    requirements: list[Requirement], assessments: list[RequirementAssessment]
) -> DraftRequest:
    extraction = ExtractionResponse(
        job_title="Senior Backend Engineer",
        company="Harbor & Pine",
        requirements=requirements,
        dropped_count=0,
    )
    gap_analysis = GapAnalysisResponse(
        assessments=assessments,
        dropped_evidence_count=0,
        dropped_assessment_count=0,
        synthesized_assessment_count=0,
    )
    return DraftRequest(extraction=extraction, gap_analysis=gap_analysis)


def test_draft_request_requires_complete_revision_context():
    requirement = req("Python")
    request = request_with_gap(
        [requirement],
        [assessment(requirement, AssessmentOutcome.MATCH, [evidence("Python", ProfileEvidenceSource.SKILLS)])],
    )
    finding = CritiqueFinding(
        code=FindingCode.GENERIC_TONE,
        severity=FindingSeverity.ADVISORY,
        message="Use a more specific opening.",
    )

    assert request.previous_cover_letter is None
    with pytest.raises(ValidationError):
        DraftRequest(
            extraction=request.extraction,
            gap_analysis=request.gap_analysis,
            previous_cover_letter=DraftResponse(
                salutation="Dear Hiring Manager,",
                paragraphs=[
                    {"prose": "One.", "requirements": [], "evidence": []},
                    {"prose": "Two.", "requirements": [], "evidence": []},
                    {"prose": "Three.", "requirements": [], "evidence": []},
                ],
                sign_off="Sincerely,",
                candidate_name="Jordan Ellis",
                dropped_evidence_count=0,
                dropped_requirement_count=0,
            ),
        )
    with pytest.raises(ValidationError):
        DraftRequest(
            extraction=request.extraction,
            gap_analysis=request.gap_analysis,
            findings=[finding],
        )


def test_normalize_draft_output_drops_gap_and_unapproved_provenance_but_keeps_prose():
    match_requirement = req("Python")
    gap_requirement = req("Kubernetes", Necessity.PREFERRED)
    unknown_requirement = req("Terraform", Necessity.PREFERRED)
    approved = evidence("Python", ProfileEvidenceSource.SKILLS)
    output = DraftToolOutput(
        paragraphs=[
            DraftParagraphToolOutput(
                prose="A factual paragraph retained for Critique.",
                requirements=[match_requirement, gap_requirement, unknown_requirement],
                evidence=[
                    approved,
                    evidence("Kubernetes", ProfileEvidenceSource.SKILLS),
                    evidence("Terraform", ProfileEvidenceSource.SKILLS),
                ],
            ),
            DraftParagraphToolOutput(prose="A closing paragraph.", requirements=[], evidence=[]),
            DraftParagraphToolOutput(prose="Another paragraph.", requirements=[], evidence=[]),
        ]
    )
    request = request_with_gap(
        [match_requirement, gap_requirement],
        [assessment(match_requirement, AssessmentOutcome.MATCH, [approved]), assessment(gap_requirement, AssessmentOutcome.GAP)],
    )

    response = normalize_draft_output(request, output, PROFILE)

    assert response.candidate_name == "Jordan Ellis"
    assert response.salutation == "Dear Hiring Manager,"
    assert response.sign_off == "Sincerely,"
    assert response.paragraphs[0].prose == "A factual paragraph retained for Critique."
    assert response.paragraphs[0].requirements == [match_requirement]
    assert response.paragraphs[0].evidence == [approved]
    assert response.dropped_requirement_count == 2
    assert response.dropped_evidence_count == 2


def full_mock_request() -> DraftRequest:
    python = req("3–5 years of experience building production APIs with Python")
    communication = req("Strong written and verbal communication skills")
    aws = req("Experience with AWS (Lambda, RDS, S3)")
    ecommerce = req("Experience with e-commerce platforms.")
    kubernetes = req("Familiarity with Kubernetes", Necessity.PREFERRED)
    graphql = req("Experience designing GraphQL APIs", Necessity.PREFERRED)
    customer = req("A thoughtful, customer-focused approach to solving problems", Necessity.UNSTATED)
    return request_with_gap(
        [python, communication, aws, ecommerce, kubernetes, graphql, customer],
        [
            assessment(python, AssessmentOutcome.MATCH, [evidence(PROFILE.summary, ProfileEvidenceSource.SUMMARY)]),
            assessment(communication, AssessmentOutcome.GAP),
            assessment(aws, AssessmentOutcome.MATCH, [evidence("AWS (Lambda, RDS, S3)", ProfileEvidenceSource.SKILLS)]),
            assessment(ecommerce, AssessmentOutcome.ADJACENT, [evidence("Built and maintained a Django/PostgreSQL inventory system serving 200+ retail locations", ProfileEvidenceSource.EXPERIENCE)]),
            assessment(kubernetes, AssessmentOutcome.ADJACENT, [evidence("Docker", ProfileEvidenceSource.SKILLS)]),
            assessment(graphql, AssessmentOutcome.ADJACENT, [evidence("REST API design", ProfileEvidenceSource.SKILLS)]),
            assessment(customer, AssessmentOutcome.GAP),
        ],
    )


def test_mock_draft_returns_complete_grounded_structured_letter():
    response = draft(full_mock_request(), PROFILE)

    assert len(response.paragraphs) == 4
    assert response.candidate_name == PROFILE.name
    assert "I have led platform teams" in response.paragraphs[0].prose
    assert response.dropped_evidence_count == 0
    assert response.dropped_requirement_count == 0
    assert all(paragraph.prose for paragraph in response.paragraphs)
    assert response.paragraphs[2].requirements[-1].text == "Experience designing GraphQL APIs"


def test_mock_revision_fixes_one_blocking_finding_and_then_passes():
    initial_request = full_mock_request()
    initial_letter = draft(initial_request, PROFILE)
    initial_critique_request = CritiqueRequest(
        extraction=initial_request.extraction,
        gap_analysis=initial_request.gap_analysis,
        cover_letter=initial_letter,
    )

    first_critique = critique(initial_critique_request)
    revision_request = DraftRequest(
        extraction=initial_request.extraction,
        gap_analysis=initial_request.gap_analysis,
        previous_cover_letter=initial_letter,
        findings=first_critique.findings,
    )
    revised_letter = draft(revision_request, PROFILE)
    second_critique = critique(
        CritiqueRequest(
            extraction=initial_request.extraction,
            gap_analysis=initial_request.gap_analysis,
            cover_letter=revised_letter,
        )
    )

    assert first_critique.verdict.value == "revise"
    assert any(finding.code is FindingCode.UNSUPPORTED_CLAIM for finding in first_critique.findings)
    assert "I have led platform teams" not in revised_letter.paragraphs[0].prose
    assert second_critique.verdict.value == "pass"


def test_draft_response_requires_three_to_four_paragraphs():
    with pytest.raises(ValidationError):
        DraftResponse(
            salutation="Dear Hiring Manager,",
            paragraphs=[],
            sign_off="Sincerely,",
            candidate_name="Jordan Ellis",
            dropped_evidence_count=0,
            dropped_requirement_count=0,
        )


def test_draft_endpoint_returns_complete_typed_letter():
    request = full_mock_request()

    with TestClient(app) as client:
        response = client.post("/draft", json=request.model_dump(mode="json"))

    assert response.status_code == 200
    assert set(response.json()) == {
        "salutation",
        "paragraphs",
        "sign_off",
        "candidate_name",
        "dropped_evidence_count",
        "dropped_requirement_count",
    }
    assert response.json()["candidate_name"] == "Jordan Ellis"
    assert len(response.json()["paragraphs"]) == 4
