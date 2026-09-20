import json
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
async def test_openrouter_structured_output_live() -> None:
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

    schema = {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "string",
                },
                "minItems": 1,
                "maxItems": 2,
            }
        },
        "required": ["queries"],
        "additionalProperties": False,
    }

    response = await provider.complete(
        LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.SYSTEM,
                    content=(
                        "Generate concise web search queries. Follow the requested output schema."
                    ),
                ),
                LLMMessage(
                    role=LLMRole.USER,
                    content=(
                        "Generate one or two concise search queries about Python 3.15 changes."
                    ),
                ),
            ],
            response_schema=schema,
            response_schema_name="research_plan",
            max_output_tokens=1000,
        )
    )

    parsed = json.loads(response.content)

    assert isinstance(
        parsed["queries"],
        list,
    )

    assert 1 <= len(parsed["queries"]) <= 2

    assert all(isinstance(query, str) and query.strip() for query in parsed["queries"])

    assert response.model
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
