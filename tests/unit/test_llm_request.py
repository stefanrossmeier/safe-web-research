import pytest
from pydantic import ValidationError

from safe_web_research.domain import (
    LLMMessage,
    LLMRequest,
    LLMRole,
)


def test_llm_request_accepts_structured_output_schema() -> None:
    request = LLMRequest(
        messages=[
            LLMMessage(
                role=LLMRole.USER,
                content="test",
            )
        ],
        response_schema={
            "type": "object",
        },
        response_schema_name="result",
        max_output_tokens=500,
    )

    assert request.response_schema_name == "result"
    assert request.max_output_tokens == 500


def test_llm_request_rejects_invalid_schema_name() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.USER,
                    content="test",
                )
            ],
            response_schema={
                "type": "object",
            },
            response_schema_name=("invalid schema name"),
        )


def test_llm_request_rejects_zero_output_tokens() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.USER,
                    content="test",
                )
            ],
            max_output_tokens=0,
        )
