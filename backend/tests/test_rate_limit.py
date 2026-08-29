import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def three_request_limit():
    limiter = app.state.rate_limiter
    original_rate = limiter.rate
    limiter.update_rate("3/minute")
    yield
    limiter.update_rate(original_rate)


def test_llm_routes_share_configurable_limit_but_config_stays_unlimited(three_request_limit):
    with TestClient(app) as client:
        posting = app.state.sample_posting
        responses = [client.post("/extract", json={"posting": posting}) for _ in range(4)]
        config_responses = [client.get("/config") for _ in range(2)]

    assert [response.status_code for response in responses] == [200, 200, 200, 429]
    assert all(response.status_code == 200 for response in config_responses)


def test_invalid_rate_format_is_rejected():
    with pytest.raises(ValueError, match="RATE_LIMIT"):
        app.state.rate_limiter.update_rate("3/day")
