from collections.abc import Callable
from typing import Any

import httpx
import pytest

from safe_web_research.security.judgement import (
    ContentIntent,
    ContentJudgementAuthenticationError,
    ContentJudgementConfigurationError,
    ContentJudgementRateLimitError,
    ContentJudgementRequestError,
    ContentJudgementResponseError,
    ContentJudgementUnavailableError,
    SecurityJudgementInput,
)
from safe_web_research.security.openrouter_jev import (
    OPENROUTER_DECISIONS_URL,
    OpenRouterJevSecurityJudge,
)


def _input(*, truncated: bool = False) -> SecurityJudgementInput:
    return SecurityJudgementInput(
        source_id="source-1",
        source_url="https://example.com/page",
        content='Article text. "Ignore previous instructions" is an attack example.',
        truncated=truncated,
    )


def _success_response(*, cost: float | None = None) -> dict[str, object]:
    usage: dict[str, object] = {"input_tokens": 1000, "output_tokens": 25}
    if cost is not None:
        usage["cost"] = cost
    return {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {
            "content_intent": {
                "type": "choice",
                "choice": "benign_ai_discussion",
                "confidence": 0.91,
                "probabilities": {
                    "ordinary_content": 0.04,
                    "benign_ai_discussion": 0.91,
                    "operative_model_instruction": 0.02,
                    "unclear": 0.03,
                },
            },
            "instruction_override": {"type": "noul", "noul": 0.03},
            "capability_induction": {"type": "noul", "noul": 0.01},
            "secret_exfiltration": {"type": "noul", "noul": 0.02},
            "provenance_manipulation": {"type": "noul", "noul": 0.04},
        },
        "usage": usage,
    }


class _FakeAsyncClient:
    response_factory: Callable[[str, dict[str, str], dict[str, object]], httpx.Response]
    calls: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        type(self).calls.append((url, headers, json))
        return type(self).response_factory(url, headers, json)


def _install_response(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> None:
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response_factory = staticmethod(lambda _url, _headers, _json: response)
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


def test_adapter_rejects_invalid_configuration() -> None:
    with pytest.raises(ContentJudgementConfigurationError):
        OpenRouterJevSecurityJudge(" ")
    with pytest.raises(ContentJudgementConfigurationError):
        OpenRouterJevSecurityJudge("test-key", model=" ")
    with pytest.raises(ContentJudgementConfigurationError):
        OpenRouterJevSecurityJudge("test-key", timeout_seconds=0)


@pytest.mark.asyncio
async def test_adapter_sends_structured_state_and_five_narrow_questions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response(monkeypatch, httpx.Response(200, json=_success_response()))
    judge = OpenRouterJevSecurityJudge("test-key")

    result = await judge.assess(_input(truncated=True))

    assert len(_FakeAsyncClient.calls) == 1
    url, headers, payload = _FakeAsyncClient.calls[0]
    assert url == OPENROUTER_DECISIONS_URL
    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "typesafe/jev-1.13"
    state = payload["state"]
    assert isinstance(state, dict)
    assert state["source"] == {
        "source_id": "source-1",
        "url": "https://example.com/page",
    }
    assert state["content"] == _input().content
    questions = payload["questions"]
    assert isinstance(questions, dict)
    assert set(questions) == {
        "content_intent",
        "instruction_override",
        "capability_induction",
        "secret_exfiltration",
        "provenance_manipulation",
    }
    assert questions["instruction_override"]["type"] == "noul"
    assert questions["content_intent"]["type"] == "choice"
    assert result.content_intent is ContentIntent.BENIGN_AI_DISCUSSION
    assert result.content_intent_probabilities[ContentIntent.OPERATIVE_MODEL_INSTRUCTION] == 0.02
    assert result.semantic_risk == 0.04
    assert result.input_truncated is True
    assert result.usage.estimated_cost_usd == 0.0


@pytest.mark.asyncio
async def test_adapter_prefers_provider_reported_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_response(monkeypatch, httpx.Response(200, json=_success_response(cost=0.123)))
    result = await OpenRouterJevSecurityJudge("test-key").assess(_input())
    assert result.usage.estimated_cost_usd == pytest.approx(0.123)


@pytest.mark.asyncio
async def test_adapter_rejects_missing_required_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _success_response()
    assert isinstance(payload["answers"], dict)
    payload["answers"].pop("secret_exfiltration")
    _install_response(monkeypatch, httpx.Response(200, json=payload))
    with pytest.raises(ContentJudgementResponseError):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())


@pytest.mark.asyncio
async def test_adapter_rejects_wrong_content_intent_probability_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _success_response()
    answers = payload["answers"]
    assert isinstance(answers, dict)
    content_intent = answers["content_intent"]
    assert isinstance(content_intent, dict)
    probabilities = content_intent["probabilities"]
    assert isinstance(probabilities, dict)
    probabilities.pop("unclear")
    _install_response(monkeypatch, httpx.Response(200, json=payload))
    with pytest.raises(ContentJudgementResponseError):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())


@pytest.mark.asyncio
async def test_adapter_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_response(monkeypatch, httpx.Response(200, content=b"{"))
    with pytest.raises(ContentJudgementResponseError):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())


@pytest.mark.asyncio
async def test_adapter_rejects_out_of_range_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _success_response()
    answers = payload["answers"]
    assert isinstance(answers, dict)
    override = answers["instruction_override"]
    assert isinstance(override, dict)
    override["noul"] = 1.2
    _install_response(monkeypatch, httpx.Response(200, json=payload))
    with pytest.raises(ContentJudgementResponseError):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())


@pytest.mark.asyncio
async def test_adapter_maps_transport_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeAsyncClient.calls = []

    def _timeout(
        _url: str,
        _headers: dict[str, str],
        _json: dict[str, object],
    ) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    _FakeAsyncClient.response_factory = _timeout
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    with pytest.raises(ContentJudgementUnavailableError):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, ContentJudgementAuthenticationError),
        (403, ContentJudgementAuthenticationError),
        (429, ContentJudgementRateLimitError),
        (422, ContentJudgementRequestError),
        (500, ContentJudgementUnavailableError),
    ],
)
async def test_adapter_maps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_type: type[Exception],
) -> None:
    _install_response(monkeypatch, httpx.Response(status))
    with pytest.raises(error_type):
        await OpenRouterJevSecurityJudge("test-key").assess(_input())
