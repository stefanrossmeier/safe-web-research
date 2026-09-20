import json

import pytest

from safe_web_research.domain import (
    LLMResponse,
    LLMUsage,
    ResearchBudget,
    ResearchRequest,
)
from safe_web_research.llm import (
    FakeLLMProvider,
)
from safe_web_research.research import (
    ResearchPlanner,
    ResearchPlanningError,
)


@pytest.mark.asyncio
async def test_planner_returns_normalized_bounded_queries() -> None:
    llm = FakeLLMProvider(
        [
            LLMResponse(
                content=json.dumps(
                    {
                        "queries": [
                            "  Python   3.15 changes  ",
                            "python 3.15 changes",
                            "Python 3.15 release notes",
                        ]
                    }
                ),
                model="fake-planner",
                usage=LLMUsage(
                    input_tokens=20,
                    output_tokens=10,
                    estimated_cost_usd=0.001,
                ),
            )
        ]
    )

    planner = ResearchPlanner(llm)

    outcome = await planner.plan(
        ResearchRequest(
            question=("What changed in Python 3.15?"),
            budget=ResearchBudget(max_searches=2),
            allowed_domains=["python.org"],
        ),
        max_output_tokens=300,
    )

    assert outcome.plan.queries == [
        "Python 3.15 changes",
        "Python 3.15 release notes",
    ]

    assert outcome.model == "fake-planner"
    assert outcome.usage.input_tokens == 20

    sent = llm.requests[0]

    assert sent.max_output_tokens == 300

    assert sent.response_schema_name == "research_plan"

    assert sent.response_schema is not None

    properties = sent.response_schema["properties"]

    assert isinstance(
        properties,
        dict,
    )

    queries_schema = properties["queries"]

    assert isinstance(
        queries_schema,
        dict,
    )

    assert queries_schema["maxItems"] == 2

    assert "python.org" in sent.messages[1].content


@pytest.mark.asyncio
async def test_planner_rejects_too_many_queries_even_if_fake_provider_ignores_schema() -> None:
    llm = FakeLLMProvider(
        [
            LLMResponse(
                content=json.dumps(
                    {
                        "queries": [
                            "one",
                            "two",
                        ]
                    }
                ),
                model="fake",
            )
        ]
    )

    planner = ResearchPlanner(llm)

    with pytest.raises(
        ResearchPlanningError,
        match="exceeded",
    ):
        await planner.plan(
            ResearchRequest(
                question="test",
                budget=ResearchBudget(max_searches=1),
            ),
            max_output_tokens=100,
        )


@pytest.mark.asyncio
async def test_planner_rejects_invalid_output() -> None:
    planner = ResearchPlanner(
        FakeLLMProvider(
            [
                LLMResponse(
                    content='{"wrong": []}',
                    model="fake",
                )
            ]
        )
    )

    with pytest.raises(
        ResearchPlanningError,
        match="invalid plan",
    ):
        await planner.plan(
            ResearchRequest(question="test"),
            max_output_tokens=100,
        )
