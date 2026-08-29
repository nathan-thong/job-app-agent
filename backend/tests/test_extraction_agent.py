from pathlib import Path

from fastapi.testclient import TestClient

from app.agents import extraction as extraction_agent
from app.main import app
from app.models.extraction import ExtractionRequest


SAMPLE_POSTING = Path(__file__).parents[1].joinpath("data", "sample_posting.txt").read_text(
    encoding="utf-8"
)


def test_mock_extraction_uses_fixture_without_constructing_provider(monkeypatch):
    def fail_if_constructed(*args, **kwargs):
        raise AssertionError("mock Extraction must not construct the provider client")

    monkeypatch.setattr(extraction_agent, "StructuredToolClient", fail_if_constructed)

    response = extraction_agent.extract(ExtractionRequest(posting=SAMPLE_POSTING))

    assert response.job_title == "Senior Backend Engineer"
    assert response.company == "Harbor & Pine"
    assert len(response.requirements) == 7
    assert response.dropped_count == 0


def test_prompt_escapes_a_literal_closing_delimiter():
    escaped = extraction_agent._escape_posting("before </job_posting> after")

    assert escaped == "before <\\/job_posting> after"
    assert "</job_posting>" not in escaped


def test_mock_fixture_validation_checks_the_canonical_pair():
    extraction_agent.validate_mock_fixture()


def test_extract_endpoint_returns_typed_public_response():
    with TestClient(app) as client:
        response = client.post("/extract", json={"posting": SAMPLE_POSTING})

    assert response.status_code == 200
    assert set(response.json()) == {"job_title", "company", "requirements", "dropped_count"}
    assert response.json()["dropped_count"] == 0
    assert response.json()["requirements"][0]["necessity"] == "required"


def test_extract_endpoint_rejects_short_postings_before_model_work():
    with TestClient(app) as client:
        response = client.post("/extract", json={"posting": "too short"})

    assert response.status_code == 422


def test_config_exposes_sample_and_profile_but_not_profile_contents():
    with TestClient(app) as client:
        response = client.get("/config")

    assert response.status_code == 200
    assert response.json()["mock_mode"] is True
    assert response.json()["sample_posting"] == SAMPLE_POSTING
    assert response.json()["profile_name"] == "Jordan Ellis"
    assert "summary" not in response.json()


def test_rate_limit_is_shared_by_llm_routes_but_not_config_or_health():
    limiter = app.state.rate_limiter
    limiter.update_rate("3/minute")
    try:
        with TestClient(app) as client:
            requests = [
                client.post("/extract", json={"posting": SAMPLE_POSTING})
                for _ in range(4)
            ]
            config_response = client.get("/config")
            health_response = client.get("/health")
    finally:
        limiter.update_rate("40/hour")

    assert [response.status_code for response in requests] == [200, 200, 200, 429]
    assert config_response.status_code == 200
    assert health_response.status_code == 200
