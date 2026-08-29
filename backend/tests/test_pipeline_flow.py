from fastapi.testclient import TestClient

from app.main import app


def test_mock_pipeline_completes_revision_then_passes():
    with TestClient(app) as client:
        extraction_response = client.post(
            "/extract", json={"posting": app.state.sample_posting}
        )
        extraction = extraction_response.json()

        gap_response = client.post("/gap-analysis", json={"extraction": extraction})
        gap_analysis = gap_response.json()

        draft_response = client.post(
            "/draft",
            json={"extraction": extraction, "gap_analysis": gap_analysis},
        )
        draft = draft_response.json()

        critique_response = client.post(
            "/critique",
            json={
                "extraction": extraction,
                "gap_analysis": gap_analysis,
                "cover_letter": draft,
            },
        )
        critique = critique_response.json()

        revision_response = client.post(
            "/draft",
            json={
                "extraction": extraction,
                "gap_analysis": gap_analysis,
                "previous_cover_letter": draft,
                "findings": critique["findings"],
            },
        )
        revision = revision_response.json()

        final_critique_response = client.post(
            "/critique",
            json={
                "extraction": extraction,
                "gap_analysis": gap_analysis,
                "cover_letter": revision,
            },
        )
        final_critique = final_critique_response.json()

    assert [
        extraction_response.status_code,
        gap_response.status_code,
        draft_response.status_code,
        critique_response.status_code,
        revision_response.status_code,
        final_critique_response.status_code,
    ] == [200, 200, 200, 200, 200, 200]
    assert len(extraction["requirements"]) > 0
    assert len(gap_analysis["assessments"]) == len(extraction["requirements"])
    assert critique["verdict"] == "revise"
    assert final_critique["verdict"] == "pass"
    assert "I have led platform teams" in draft["paragraphs"][0]["prose"]
    assert "I have led platform teams" not in revision["paragraphs"][0]["prose"]
