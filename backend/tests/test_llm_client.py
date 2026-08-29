from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.llm.client import StructuredCallError, StructuredToolClient


class Output(BaseModel):
    answer: str


class FakeMessages:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def tool_response(value, stop_reason="tool_use"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="tool_use", input=value)],
    )


def test_structured_client_uses_provider_schema_and_parser():
    provider = FakeClient([tool_response({"answer": "done"})])
    client = StructuredToolClient(api_key="test-key", model_name="test-model", client=provider)

    result = client.call(
        system_prompt="system",
        user_prompt="user",
        output_model=Output,
        parser=Output.model_validate,
        max_tokens=128,
    )

    assert result == Output(answer="done")
    call = provider.messages.calls[0]
    assert call["model"] == "test-model"
    assert call["max_tokens"] == 128
    assert call["timeout"] == 30.0
    assert call["tools"][0]["input_schema"] == Output.model_json_schema()
    assert call["tool_choice"] == {"type": "tool", "name": "structured_output"}


def test_structured_client_retries_one_malformed_tool_output():
    provider = FakeClient(
        [
            tool_response({"unexpected": "shape"}),
            tool_response({"answer": "recovered"}),
        ]
    )
    client = StructuredToolClient(api_key="test-key", model_name="test-model", client=provider)

    result = client.call(
        system_prompt="system",
        user_prompt="user",
        output_model=Output,
        parser=Output.model_validate,
        max_tokens=128,
    )

    assert result == Output(answer="recovered")
    assert len(provider.messages.calls) == 2


def test_structured_client_retries_when_no_tool_output_is_returned():
    provider = FakeClient(
        [
            SimpleNamespace(stop_reason="end_turn", content=[]),
            tool_response({"answer": "recovered"}),
        ]
    )
    client = StructuredToolClient(api_key="test-key", model_name="test-model", client=provider)

    result = client.call(
        system_prompt="system",
        user_prompt="user",
        output_model=Output,
        parser=Output.model_validate,
        max_tokens=128,
    )

    assert result == Output(answer="recovered")
    assert len(provider.messages.calls) == 2


def test_structured_client_does_not_retry_max_tokens_truncation():
    provider = FakeClient([tool_response({}, stop_reason="max_tokens"), tool_response({"answer": "nope"})])
    client = StructuredToolClient(api_key="test-key", model_name="test-model", client=provider)

    with pytest.raises(StructuredCallError, match="truncated"):
        client.call(
            system_prompt="system",
            user_prompt="user",
            output_model=Output,
            parser=Output.model_validate,
            max_tokens=128,
        )

    assert len(provider.messages.calls) == 1
