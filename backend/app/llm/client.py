import logging
from collections.abc import Callable
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError


ParsedOutput = TypeVar("ParsedOutput")
logger = logging.getLogger(__name__)


class StructuredCallError(Exception):
    """A sanitized failure from a structured provider call."""


class StructuredToolClient:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: float = 30.0,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._client = client or anthropic.Anthropic(api_key=api_key)

    def call(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
        parser: Callable[[Any], ParsedOutput],
        max_tokens: int,
    ) -> ParsedOutput:
        tool = {
            "name": "structured_output",
            "description": "Return the requested structured output.",
            "input_schema": output_model.model_json_schema(),
        }

        for attempt in range(2):
            try:
                response = self._client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    timeout=self.timeout_seconds,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    tools=[tool],
                    tool_choice={"type": "tool", "name": tool["name"]},
                )
                if getattr(response, "stop_reason", None) == "max_tokens":
                    logger.warning(
                        "structured_call_truncated",
                        extra={"model": self.model_name, "reason": "max_tokens"},
                    )
                    raise StructuredCallError("The model response was truncated.")
                raw_output = self._tool_input(response)
                return parser(raw_output)
            except StructuredCallError:
                raise
            except (ValidationError, TypeError, KeyError, IndexError, AttributeError, ValueError) as exc:
                if attempt == 0:
                    continue
                raise StructuredCallError("The model returned an invalid structured response.") from exc
            except (anthropic.APIConnectionError, anthropic.APITimeoutError, TimeoutError, OSError) as exc:
                if attempt == 0:
                    continue
                raise StructuredCallError("The model provider could not be reached.") from exc
            except anthropic.APIStatusError as exc:
                if 400 <= exc.status_code < 500:
                    raise StructuredCallError("The model provider rejected the request.") from exc
                if attempt == 0:
                    continue
                raise StructuredCallError("The model provider returned an unavailable response.") from exc

        raise StructuredCallError("The model provider returned an invalid response.")

    @staticmethod
    def _tool_input(response: Any) -> Any:
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "tool_use":
                return block.input
        raise ValueError("No structured tool output was returned.")
