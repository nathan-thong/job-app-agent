import pytest
from pydantic import ValidationError

from app.models.extraction import (
    ExtractionRequest,
    ExtractionResponse,
    ExtractionToolOutput,
    Necessity,
    Requirement,
)


def test_extraction_request_enforces_posting_bounds():
    with pytest.raises(ValidationError):
        ExtractionRequest(posting="too short")

    with pytest.raises(ValidationError):
        ExtractionRequest(posting="x" * 8_001)

    request = ExtractionRequest(posting="x" * 50)
    assert request.posting == "x" * 50


def test_requirement_has_only_verbatim_text_and_necessity():
    requirement = Requirement(text="Build Python services", necessity=Necessity.REQUIRED)

    assert set(requirement.model_dump()) == {"text", "necessity"}
    with pytest.raises(ValidationError):
        Requirement(
            text="Build Python services",
            necessity="required",
            kind="technical",
        )


def test_necessity_is_a_closed_string_enum():
    assert [necessity.value for necessity in Necessity] == [
        "required",
        "preferred",
        "unstated",
    ]
    with pytest.raises(ValidationError):
        Requirement(text="Build Python services", necessity="important")


def test_tool_output_and_response_keep_separate_shapes():
    requirement = Requirement(text="Build Python services", necessity=Necessity.REQUIRED)
    tool_output = ExtractionToolOutput(
        job_title="Senior Backend Engineer",
        company="Harbor & Pine",
        requirements=[requirement],
    )
    response = ExtractionResponse(
        job_title=tool_output.job_title,
        company=tool_output.company,
        requirements=tool_output.requirements,
        dropped_count=0,
    )

    assert set(tool_output.model_dump()) == {"job_title", "company", "requirements"}
    assert set(response.model_dump()) == {
        "job_title",
        "company",
        "requirements",
        "dropped_count",
    }
    assert ExtractionResponse.model_fields["dropped_count"].is_required()

    with pytest.raises(ValidationError):
        ExtractionResponse(
            job_title=None,
            company=None,
            requirements=[requirement],
        )
