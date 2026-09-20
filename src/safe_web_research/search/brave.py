from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

import httpx
from pydantic import BaseModel, ConfigDict, HttpUrl, ValidationError

from safe_web_research.domain.search import SearchRequest, SearchResult
from safe_web_research.search.base import SearchProvider
from safe_web_research.search.errors import (
    SearchProviderAuthenticationError,
    SearchProviderConfigurationError,
    SearchProviderRateLimitError,
    SearchProviderRequestError,
    SearchProviderResponseError,
    SearchProviderUnavailableError,
)

BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

BRAVE_MAX_QUERY_CHARACTERS = 600
BRAVE_MAX_QUERY_WORDS = 75


class _BraveWireModel(BaseModel):
    """Base model for Brave wire responses.

    Unknown provider fields are deliberately ignored because Brave may
    add backwards-compatible fields without changing our domain contract.
    """

    model_config = ConfigDict(extra="ignore")


class _BraveWebResult(_BraveWireModel):
    title: str
    url: str
    description: str | None = None


class _BraveWebResults(_BraveWireModel):
    results: list[_BraveWebResult]


class _BraveResponse(_BraveWireModel):
    web: _BraveWebResults | None = None


class BraveSearchProvider(SearchProvider):
    """Brave Web Search API adapter."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 10.0,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        api_key = api_key.strip()

        if not api_key:
            raise SearchProviderConfigurationError("Brave Search API key must not be empty")

        if timeout_seconds <= 0:
            raise SearchProviderConfigurationError("Brave Search timeout must be greater than zero")

        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._today_provider = today_provider or self._utc_today

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        query = self._build_query(request)

        params: dict[str, str | int | bool] = {
            "q": query,
            "count": request.max_results,
            "spellcheck": False,
            "text_decorations": False,
        }

        if request.country is not None:
            params["country"] = request.country.upper()

        if request.language is not None:
            params["search_lang"] = request.language.lower()

        if request.freshness_days is not None:
            params["freshness"] = self._build_freshness(request.freshness_days)

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._api_key,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.get(
                    BRAVE_WEB_SEARCH_URL,
                    params=params,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise SearchProviderUnavailableError("Brave Search request timed out") from exc
        except httpx.RequestError as exc:
            raise SearchProviderUnavailableError("Brave Search request failed") from exc

        self._raise_for_status(response)

        try:
            payload = _BraveResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise SearchProviderResponseError("Brave Search returned an invalid response") from exc

        if payload.web is None:
            return []

        results: list[SearchResult] = []

        for rank, result in enumerate(payload.web.results, start=1):
            try:
                normalized = SearchResult(
                    result_id=self._result_id(result.url),
                    url=HttpUrl(result.url),
                    title=result.title,
                    snippet=result.description or "",
                    rank=rank,
                    provider="brave",
                )
            except ValidationError as exc:
                raise SearchProviderResponseError(
                    "Brave Search returned an invalid web result"
                ) from exc

            results.append(normalized)

        return results

    def _build_query(self, request: SearchRequest) -> str:
        parts = [request.query]

        if request.include_domains:
            include_filter = " OR ".join(f"site:{domain}" for domain in request.include_domains)

            if len(request.include_domains) == 1:
                parts.append(include_filter)
            else:
                parts.append(f"({include_filter})")

        parts.extend(f"NOT site:{domain}" for domain in request.exclude_domains)

        query = " ".join(parts)

        if len(query) > BRAVE_MAX_QUERY_CHARACTERS:
            raise SearchProviderRequestError("Brave Search query exceeds the 600 character limit")

        if len(query.split()) > BRAVE_MAX_QUERY_WORDS:
            raise SearchProviderRequestError("Brave Search query exceeds the 75 word limit")

        return query

    def _build_freshness(self, freshness_days: int) -> str:
        presets = {
            1: "pd",
            7: "pw",
            31: "pm",
            365: "py",
        }

        preset = presets.get(freshness_days)

        if preset is not None:
            return preset

        end = self._today_provider()
        start = end - timedelta(days=freshness_days - 1)

        return f"{start.isoformat()}to{end.isoformat()}"

    @staticmethod
    def _result_id(url: str) -> str:
        digest = sha256(url.encode("utf-8")).hexdigest()[:16]
        return f"brave-{digest}"

    @staticmethod
    def _utc_today() -> date:
        return datetime.now(UTC).date()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code

        if 200 <= status < 300:
            return

        if status in {401, 403}:
            raise SearchProviderAuthenticationError("Brave Search authentication failed")

        if status == 429:
            raise SearchProviderRateLimitError(
                "Brave Search rate limit exceeded",
                reset_seconds=response.headers.get("X-RateLimit-Reset"),
            )

        if status in {400, 404, 422}:
            raise SearchProviderRequestError(
                f"Brave Search rejected the request with HTTP {status}"
            )

        if 500 <= status < 600:
            raise SearchProviderUnavailableError(f"Brave Search returned HTTP {status}")

        raise SearchProviderResponseError(f"Unexpected Brave Search HTTP status {status}")
