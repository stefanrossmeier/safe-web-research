import json

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import (
    SchemaError,
)
from jsonschema.exceptions import (
    ValidationError as JSONSchemaValidationError,
)
from pydantic import BaseModel, ConfigDict, ValidationError

from safe_web_research.domain.llm import (
    LLMRequest,
    LLMResponse,
    LLMUsage,
)
from safe_web_research.llm.base import LLMProvider
from safe_web_research.llm.errors import (
    LLMProviderAuthenticationError,
    LLMProviderConfigurationError,
    LLMProviderRateLimitError,
    LLMProviderRequestError,
    LLMProviderResponseError,
    LLMProviderUnavailableError,
    LLMStructuredOutputError,
)

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class _OpenRouterWireModel(BaseModel):
    """Base model for OpenRouter wire responses."""

    model_config = ConfigDict(extra="ignore")


class _OpenRouterMessage(_OpenRouterWireModel):
    content: str | None = None


class _OpenRouterChoice(_OpenRouterWireModel):
    message: _OpenRouterMessage


class _OpenRouterUsage(_OpenRouterWireModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float | None = None


class _OpenRouterResponse(_OpenRouterWireModel):
    model: str
    choices: list[_OpenRouterChoice]
    usage: _OpenRouterUsage | None = None


class OpenRouterLLMProvider(LLMProvider):
    """Provider-neutral OpenRouter Chat Completions adapter."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "openrouter/free",
        timeout_seconds: float = 60.0,
        app_url: str | None = None,
        app_title: str | None = "safe-web-research",
    ) -> None:
        api_key = api_key.strip()
        model = model.strip()

        if not api_key:
            raise LLMProviderConfigurationError("OpenRouter API key must not be empty")

        if not model:
            raise LLMProviderConfigurationError("OpenRouter model must not be empty")

        if timeout_seconds <= 0:
            raise LLMProviderConfigurationError("OpenRouter timeout must be greater than zero")

        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._app_url = app_url.strip() if app_url else None
        self._app_title = app_title.strip() if app_title else None

    async def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        payload = self._build_payload(request)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self._app_url is not None:
            headers["HTTP-Referer"] = self._app_url

        if self._app_title is not None:
            headers["X-OpenRouter-Title"] = self._app_title

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                trust_env=False,
            ) as client:
                response = await client.post(
                    OPENROUTER_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise LLMProviderUnavailableError("OpenRouter request timed out") from exc

        except httpx.RequestError as exc:
            raise LLMProviderUnavailableError("OpenRouter request failed") from exc

        self._raise_for_status(response)

        try:
            wire = _OpenRouterResponse.model_validate(response.json())

        except (
            ValueError,
            ValidationError,
        ) as exc:
            raise LLMProviderResponseError("OpenRouter returned an invalid response") from exc

        if not wire.choices:
            raise LLMProviderResponseError("OpenRouter returned no completion choices")

        content = wire.choices[0].message.content

        if content is None:
            raise LLMProviderResponseError("OpenRouter returned no text content")

        if request.response_schema is not None:
            self._validate_structured_output(
                content,
                request.response_schema,
            )

        usage = wire.usage

        return LLMResponse(
            content=content,
            model=wire.model,
            usage=LLMUsage(
                input_tokens=(usage.prompt_tokens if usage is not None else 0),
                output_tokens=(usage.completion_tokens if usage is not None else 0),
                estimated_cost_usd=(
                    usage.cost if (usage is not None and usage.cost is not None) else 0.0
                ),
            ),
        )

    def _build_payload(
        self,
        request: LLMRequest,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "usage": {
                "include": True,
            },
        }

        if request.max_output_tokens is not None:
            payload["max_completion_tokens"] = request.max_output_tokens

        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.response_schema_name,
                    "strict": True,
                    "schema": request.response_schema,
                },
            }

            payload["provider"] = {
                "require_parameters": True,
            }

            payload["reasoning"] = {
                "effort": "low",
            }

        return payload

    @staticmethod
    def _raise_for_status(
        response: httpx.Response,
    ) -> None:
        status = response.status_code

        if 200 <= status < 300:
            return

        if status in {
            401,
            403,
        }:
            raise LLMProviderAuthenticationError("OpenRouter authentication failed")

        if status == 429:
            raise LLMProviderRateLimitError("OpenRouter rate limit exceeded")

        if status in {
            400,
            402,
            404,
            413,
            422,
        }:
            raise LLMProviderRequestError(f"OpenRouter rejected the request with HTTP {status}")

        if status == 408 or 500 <= status < 600:
            raise LLMProviderUnavailableError(f"OpenRouter returned HTTP {status}")

        raise LLMProviderResponseError(f"Unexpected OpenRouter HTTP status {status}")

    @staticmethod
    def _validate_structured_output(
        content: str,
        schema: dict[str, object],
    ) -> None:
        try:
            parsed = json.loads(content)

        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(
                "OpenRouter returned invalid JSON for a structured-output request"
            ) from exc

        try:
            validator = Draft202012Validator(schema)

            validator.check_schema(schema)

            validator.validate(parsed)

        except SchemaError as exc:
            raise LLMProviderConfigurationError(
                "The requested structured-output schema is invalid"
            ) from exc

        except JSONSchemaValidationError as exc:
            raise LLMStructuredOutputError(
                "OpenRouter returned JSON that does not match the requested schema"
            ) from exc
