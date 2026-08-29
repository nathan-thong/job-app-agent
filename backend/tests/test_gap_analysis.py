import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.gap_analysis import (
    _evidence_is_verifiable,
    analyze,
    normalize_assessments,
)
from app.models.extraction import (
    ExtractionResponse,
    Necessity,
    Requirement,
)
from app.models.gap_analysis import (
    AssessmentOutcome,
    GapAnalysisRequest,
    GapAnalysisResponse,
    GapAnalysisToolOutput,
    ProfileEvidence,
    ProfileEvidenceSource,
    RequirementAssessment,
)
from app.main import app
from app.profile import load_profile


PROFILE = load_profile()


def make_request(*requirements: Requirement) -> GapAnalysisRequest:
    return GapAnalysisRequest(
        extraction=ExtractionResponse(
            job_title="Senior Backend Engineer",
            company="Harbor & Pine",
            requirements=list(requirements),
            dropped_count=0,
        )
    )


def assessment(
    requirement: Requirement,
    outcome: AssessmentOutcome,
    reason: str = "A test reason.",
    evidence: list[ProfileEvidence] | None = None,
) -> RequirementAssessment:
    return RequirementAssessment(
        requirement=requirement,
        outcome=outcome,
        reason=reason,
        evidence=evidence or [],
    )


def evidence(text: str, source: ProfileEvidenceSource) -> ProfileEvidence:
    return ProfileEvidence(text=text, source=source)


def test_profile_evidence_is_checked_inside_its_named_section():
    assert _evidence_is_verifiable(
        evidence("AWS (Lambda, RDS, S3)", ProfileEvidenceSource.SKILLS), PROFILE
    )
    assert not _evidence_is_verifiable(
        evidence("AWS (Lambda, RDS, S3)", ProfileEvidenceSource.SUMMARY), PROFILE
    )
    assert not _evidence_is_verifiable(
        evidence("Cloud Functions", ProfileEvidenceSource.SKILLS), PROFILE
    )


def test_normalization_restores_order_and_synthesizes_omissions():
    python = Requirement(text="Python", necessity=Necessity.REQUIRED)
    aws = Requirement(text="AWS", necessity=Necessity.PREFERRED)
    kubernetes = Requirement(text="Kubernetes", necessity=Necessity.PREFERRED)
    unknown = Requirement(text="Terraform", necessity=Necessity.PREFERRED)
    request = make_request(python, aws, kubernetes)
    output = GapAnalysisToolOutput(
        assessments=[
            assessment(
                aws,
                AssessmentOutcome.MATCH,
                evidence=[evidence("AWS (Lambda, RDS, S3)", ProfileEvidenceSource.SKILLS)],
            ),
            assessment(unknown, AssessmentOutcome.MATCH),
            assessment(aws, AssessmentOutcome.GAP, reason="Duplicate"),
        ]
    )

    response = normalize_assessments(request, output, PROFILE)

    assert [item.requirement for item in response.assessments] == [python, aws, kubernetes]
    assert [item.outcome for item in response.assessments] == [
        AssessmentOutcome.GAP,
        AssessmentOutcome.MATCH,
        AssessmentOutcome.GAP,
    ]
    assert response.assessments[0].reason == "No assessment returned"
    assert response.dropped_assessment_count == 2
    assert response.synthesized_assessment_count == 2


def test_invalid_evidence_is_dropped_and_match_downgrades_when_none_survives():
    requirement = Requirement(text="GraphQL", necessity=Necessity.PREFERRED)
    request = make_request(requirement)
    output = GapAnalysisToolOutput(
        assessments=[
            assessment(
                requirement,
                AssessmentOutcome.MATCH,
                evidence=[evidence("GraphQL", ProfileEvidenceSource.SKILLS)],
            )
        ]
    )

    response = normalize_assessments(request, output, PROFILE)
    normalized = response.assessments[0]

    assert normalized.outcome is AssessmentOutcome.GAP
    assert normalized.reason == "No verifiable Profile Evidence found."
    assert normalized.evidence == []
    assert response.dropped_evidence_count == 1


def test_adjacent_survives_when_one_evidence_item_is_checked():
    requirement = Requirement(text="Kubernetes", necessity=Necessity.PREFERRED)
    request = make_request(requirement)
    output = GapAnalysisToolOutput(
        assessments=[
            assessment(
                requirement,
                AssessmentOutcome.ADJACENT,
                evidence=[
                    evidence("Docker", ProfileEvidenceSource.SKILLS),
                    evidence("Kubernetes", ProfileEvidenceSource.SKILLS),
                ],
            )
        ]
    )

    response = normalize_assessments(request, output, PROFILE)
    normalized = response.assessments[0]

    assert normalized.outcome is AssessmentOutcome.ADJACENT
    assert [item.text for item in normalized.evidence] == ["Docker"]
    assert response.dropped_evidence_count == 1


def test_gap_assessments_cannot_carry_evidence():
    requirement = Requirement(text="GraphQL", necessity=Necessity.PREFERRED)
    request = make_request(requirement)
    output = GapAnalysisToolOutput(
        assessments=[
            assessment(
                requirement,
                AssessmentOutcome.GAP,
                evidence=[evidence("Python", ProfileEvidenceSource.SKILLS)],
            )
        ]
    )

    response = normalize_assessments(request, output, PROFILE)

    assert response.assessments[0].outcome is AssessmentOutcome.GAP
    assert response.assessments[0].evidence == []
    assert response.dropped_evidence_count == 1


def test_gap_response_counters_are_required_and_shape_is_closed():
    assert GapAnalysisResponse.model_fields["dropped_evidence_count"].is_required()
    assert GapAnalysisResponse.model_fields["dropped_assessment_count"].is_required()
    assert GapAnalysisResponse.model_fields["synthesized_assessment_count"].is_required()

    with pytest.raises(ValidationError):
        GapAnalysisResponse(assessments=[])


def test_mock_gap_analysis_covers_every_extracted_requirement():
    extraction = ExtractionResponse(
        job_title="Senior Backend Engineer",
        company="Harbor & Pine",
        requirements=[
            Requirement(
                text="3–5 years of experience building production APIs with Python",
                necessity=Necessity.REQUIRED,
            ),
            Requirement(
                text="Strong written and verbal communication skills",
                necessity=Necessity.REQUIRED,
            ),
            Requirement(
                text="Experience with AWS (Lambda, RDS, S3)",
                necessity=Necessity.REQUIRED,
            ),
            Requirement(
                text="Experience with e-commerce platforms.",
                necessity=Necessity.REQUIRED,
            ),
            Requirement(text="Familiarity with Kubernetes", necessity=Necessity.PREFERRED),
            Requirement(text="Experience designing GraphQL APIs", necessity=Necessity.PREFERRED),
            Requirement(
                text="A thoughtful, customer-focused approach to solving problems",
                necessity=Necessity.UNSTATED,
            ),
        ],
        dropped_count=0,
    )

    response = analyze(GapAnalysisRequest(extraction=extraction), PROFILE)

    assert len(response.assessments) == 7
    assert response.dropped_evidence_count == 0
    assert response.dropped_assessment_count == 0
    assert response.synthesized_assessment_count == 0
    assert any(item.outcome is AssessmentOutcome.ADJACENT for item in response.assessments)


def test_gap_analysis_endpoint_accepts_extraction_response_and_returns_typed_body():
    extraction = make_request(
        Requirement(text="AWS", necessity=Necessity.REQUIRED),
        Requirement(text="Kubernetes", necessity=Necessity.PREFERRED),
    )

    with TestClient(app) as client:
        response = client.post("/gap-analysis", json=extraction.model_dump(mode="json"))

    assert response.status_code == 200
    assert set(response.json()) == {
        "assessments",
        "dropped_evidence_count",
        "dropped_assessment_count",
        "synthesized_assessment_count",
    }
    assert [item["requirement"]["text"] for item in response.json()["assessments"]] == [
        "AWS",
        "Kubernetes",
    ]
