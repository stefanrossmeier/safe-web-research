import json

import httpx
import pytest
import respx

from safe_web_research.domain import (
    LLMMessage,
    LLMRequest,
    LLMRole,
)
from safe_web_research.llm import (
    LLMProviderAuthenticationError,
    LLMProviderRateLimitError,
    LLMProviderRequestError,
    LLMProviderResponseError,
    LLMProviderUnavailableError,
    LLMStructuredOutputError,
    OpenRouterLLMProvider,
)
from safe_web_research.llm.openrouter import (
    OPENROUTER_CHAT_COMPLETIONS_URL,
)


def _request_json(
    request: httpx.Request,
) -> dict[str, object]:
    value = json.loads(request.content.decode("utf-8"))

    assert isinstance(
        value,
        dict,
    )

    return value


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_normalizes_completion() -> None:
    route = respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "generation-1",
                "model": "example/provider-model",
                "choices": [
                    {
                        "message": {
                            "content": "hello",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "cost": 0.001,
                },
            },
        )
    )

    provider = OpenRouterLLMProvider(
        "test-key",
        model="openrouter/free",
    )

    response = await provider.complete(
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.USER,
                    content="Say hello",
                )
            ]
        )
    )

    outbound = route.calls[0].request

    assert outbound.headers["Authorization"] == "Bearer test-key"

    payload = _request_json(outbound)

    assert payload["model"] == "openrouter/free"

    assert payload["messages"] == [
        {
            "role": "user",
            "content": "Say hello",
        }
    ]

    assert payload["usage"] == {
        "include": True,
    }

    assert response.content == "hello"
    assert response.model == "example/provider-model"

    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 4
    assert response.usage.estimated_cost_usd == 0.001


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_sends_strict_json_schema() -> None:
    route = respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "structured/model",
                "choices": [{"message": {"content": '{"queries":["python"]}'}}],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 5,
                },
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    schema = {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "string",
                },
            }
        },
        "required": ["queries"],
        "additionalProperties": False,
    }

    await provider.complete(
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.USER,
                    content="Plan searches",
                )
            ],
            response_schema=schema,
            response_schema_name="research_plan",
            max_output_tokens=200,
        )
    )

    payload = _request_json(route.calls[0].request)

    assert payload["max_completion_tokens"] == 200

    assert payload["provider"] == {
        "require_parameters": True,
    }

    assert payload["reasoning"] == {
        "effort": "low",
    }

    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "research_plan",
            "strict": True,
            "schema": schema,
        },
    }


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_maps_authentication_error() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(return_value=httpx.Response(401))

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(LLMProviderAuthenticationError):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_maps_rate_limit() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(return_value=httpx.Response(429))

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(LLMProviderRateLimitError):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@pytest.mark.parametrize(
    "status",
    [
        400,
        402,
        404,
        413,
        422,
    ],
)
@respx.mock
@pytest.mark.asyncio
async def test_openrouter_maps_request_errors(
    status: int,
) -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(return_value=httpx.Response(status))

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(LLMProviderRequestError):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_includes_sanitized_provider_request_error_message() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "message": "  Context\n length   exceeded.  ",
                    "metadata": {
                        "raw": "secret request body must not appear",
                    },
                },
                "request": {
                    "messages": [
                        {
                            "content": "sensitive prompt must not appear",
                        }
                    ]
                },
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMProviderRequestError,
        match=(
            r"OpenRouter rejected the request with HTTP 400: "
            r"Context length exceeded\."
        ),
    ) as exc_info:
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )

    message = str(exc_info.value)

    assert "secret request body" not in message
    assert "sensitive prompt" not in message


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_ignores_non_json_request_error_body() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            413,
            text="raw upstream body that must not be exposed",
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMProviderRequestError,
        match=r"OpenRouter rejected the request with HTTP 413$",
    ) as exc_info:
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )

    assert "raw upstream body" not in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_maps_server_error() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(return_value=httpx.Response(503))

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(LLMProviderUnavailableError):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_rejects_empty_choices() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [],
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMProviderResponseError,
        match="no completion choices",
    ):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_rejects_missing_content() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [
                    {
                        "message": {
                            "content": None,
                        }
                    }
                ],
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMProviderResponseError,
        match="no text content",
    ):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ]
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_rejects_invalid_json_for_structured_output() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [
                    {
                        "message": {
                            "content": "not json",
                        }
                    }
                ],
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMStructuredOutputError,
        match="invalid JSON",
    ):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ],
                response_schema={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                        }
                    },
                    "required": ["value"],
                    "additionalProperties": False,
                },
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_reports_truncated_structured_output() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": '{"value":"truncated',
                        },
                    }
                ],
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMStructuredOutputError,
        match="completion token limit was reached",
    ):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ],
                response_schema={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                        }
                    },
                    "required": ["value"],
                    "additionalProperties": False,
                },
            )
        )


@respx.mock
@pytest.mark.asyncio
async def test_openrouter_rejects_json_that_violates_schema() -> None:
    respx.post(OPENROUTER_CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [
                    {
                        "message": {
                            "content": '{"wrong":"field"}',
                        }
                    }
                ],
            },
        )
    )

    provider = OpenRouterLLMProvider("test-key")

    with pytest.raises(
        LLMStructuredOutputError,
        match="does not match",
    ):
        await provider.complete(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role=LLMRole.USER,
                        content="test",
                    )
                ],
                response_schema={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                        }
                    },
                    "required": ["value"],
                    "additionalProperties": False,
                },
            )
        )
