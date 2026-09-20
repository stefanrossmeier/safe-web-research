from enum import StrEnum

from pydantic import Field

from safe_web_research.domain.base import StrictModel


class LLMRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(StrictModel):
    """Provider-neutral chat message."""

    role: LLMRole
    content: str = Field(min_length=1)


class LLMRequest(StrictModel):
    """Provider-neutral request to a language model."""

    messages: list[LLMMessage] = Field(min_length=1)
    response_schema: dict[str, object] | None = None


class LLMUsage(StrictModel):
    """Usage reported for one language-model call."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)


class LLMResponse(StrictModel):
    """Normalized response returned by an LLM provider."""

    content: str
    model: str = Field(min_length=1)
    usage: LLMUsage = Field(default_factory=LLMUsage)
