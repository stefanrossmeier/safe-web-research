from collections import deque
from collections.abc import Sequence

from safe_web_research.domain.llm import LLMRequest, LLMResponse
from safe_web_research.llm.base import LLMProvider


class FakeLLMProvider(LLMProvider):
    """Deterministic queued LLM responses for tests."""

    def __init__(
        self,
        responses: Sequence[LLMResponse] | None = None,
    ) -> None:
        self._responses = deque(response.model_copy(deep=True) for response in (responses or []))
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request.model_copy(deep=True))

        if not self._responses:
            raise LookupError("No fake LLM response configured")

        return self._responses.popleft().model_copy(deep=True)
