from safe_web_research.domain import ResearchBudget
from safe_web_research.research import (
    BudgetTracker,
    StoppingPolicy,
)


def test_budget_tracker_enforces_search_limit() -> None:
    tracker = BudgetTracker(ResearchBudget(max_searches=1))

    assert tracker.reserve_search()
    assert not tracker.reserve_search()

    assert tracker.usage().search_requests == 1


def test_budget_tracker_consumes_fetch_attempts_even_before_success() -> None:
    tracker = BudgetTracker(
        ResearchBudget(
            max_pages=1,
            max_total_bytes=100,
        )
    )

    assert tracker.reserve_fetch() == 100
    assert tracker.reserve_fetch() is None

    usage = tracker.usage()

    assert usage.fetch_attempts == 1
    assert usage.pages_fetched == 0


def test_budget_tracker_reduces_next_page_limit_by_total_bytes() -> None:
    tracker = BudgetTracker(
        ResearchBudget(
            max_pages=2,
            max_bytes_per_page=100,
            max_total_bytes=150,
        )
    )

    assert tracker.reserve_fetch() == 100

    tracker.record_fetch_success(90)

    assert tracker.reserve_fetch() == 60


def test_stopping_policy_stops_after_configured_empty_queries() -> None:
    policy = StoppingPolicy(max_consecutive_empty_queries=2)

    assert not policy.should_stop(1)
    assert policy.should_stop(2)
