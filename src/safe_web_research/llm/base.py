from typing import Protocol

from safe_web_research.domain.llm import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    """Provider-neutral interface for language-model inference."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return one normalized language-model response."""
        ...
