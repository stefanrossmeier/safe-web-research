import os

import pytest

from safe_web_research.domain import (
    LLMMessage,
    LLMRequest,
    LLMRole,
)
from safe_web_research.llm import (
    OpenRouterLLMProvider,
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_openrouter_completion_live() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")

    model = os.getenv("OPENROUTER_TEST_MODEL")

    if not api_key:
        pytest.skip("OPENROUTER_API_KEY is not configured")

    if not model:
        pytest.skip("OPENROUTER_TEST_MODEL is not configured")

    provider = OpenRouterLLMProvider(
        api_key,
        model=model,
    )

    response = await provider.complete(
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.USER,
                    content=("Reply with exactly one short sentence explaining what SSRF is."),
                )
            ],
        )
    )

    assert response.content.strip()
    assert response.model
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
