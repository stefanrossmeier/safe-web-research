import pytest

from safe_web_research.domain import LLMUsage, ResearchBudget
from safe_web_research.research import (
    LLMBudgetTracker,
    ResearchBudgetError,
)


def test_llm_budget_caps_each_call_by_remaining_output_budget() -> None:
    tracker = LLMBudgetTracker(
        ResearchBudget(
            max_llm_calls=2,
            max_input_tokens=100,
            max_output_tokens=50,
        )
    )

    assert tracker.reserve_call(40) == 40

    tracker.record_usage(
        LLMUsage(
            input_tokens=10,
            output_tokens=30,
            estimated_cost_usd=0.01,
        )
    )

    assert tracker.reserve_call(40) == 20

    tracker.record_usage(
        LLMUsage(
            input_tokens=20,
            output_tokens=20,
            estimated_cost_usd=0.02,
        )
    )

    usage = tracker.usage()

    assert usage.llm_calls == 2
    assert usage.input_tokens == 30
    assert usage.output_tokens == 50

    assert usage.estimated_cost_usd == pytest.approx(0.03)

    assert tracker.reserve_call(1) is None


def test_llm_budget_stops_new_calls_after_input_budget_is_exhausted() -> None:
    tracker = LLMBudgetTracker(
        ResearchBudget(
            max_llm_calls=3,
            max_input_tokens=10,
            max_output_tokens=100,
        )
    )

    assert tracker.reserve_call(20) == 20

    tracker.record_usage(
        LLMUsage(
            input_tokens=10,
            output_tokens=5,
        )
    )

    assert tracker.input_budget_exhausted
    assert tracker.reserve_call(20) is None


def test_llm_budget_rejects_provider_output_overrun() -> None:
    tracker = LLMBudgetTracker(
        ResearchBudget(
            max_llm_calls=1,
            max_output_tokens=10,
        )
    )

    assert tracker.reserve_call(10) == 10

    with pytest.raises(
        ResearchBudgetError,
        match="output-token budget",
    ):
        tracker.record_usage(
            LLMUsage(
                output_tokens=11,
            )
        )
