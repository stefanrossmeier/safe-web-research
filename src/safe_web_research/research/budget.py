from dataclasses import dataclass

from safe_web_research.domain.usage import (
    ResearchBudget,
    ResearchUsage,
)


@dataclass(slots=True)
class BudgetTracker:
    """Deterministically enforce research resource budgets."""

    budget: ResearchBudget

    _search_requests: int = 0
    _fetch_attempts: int = 0
    _pages_fetched: int = 0
    _bytes_fetched: int = 0

    def reserve_search(self) -> bool:
        if self._search_requests >= self.budget.max_searches:
            return False

        self._search_requests += 1
        return True

    def reserve_fetch(self) -> int | None:
        if self._fetch_attempts >= self.budget.max_fetch_attempts:
            return None

        if self._pages_fetched >= self.budget.max_pages:
            return None

        remaining_bytes = self.budget.max_total_bytes - self._bytes_fetched

        if remaining_bytes <= 0:
            return None

        self._fetch_attempts += 1

        return min(
            self.budget.max_bytes_per_page,
            remaining_bytes,
        )

    def record_fetch_success(
        self,
        byte_count: int,
    ) -> None:
        if byte_count < 0:
            raise ValueError("byte_count must not be negative")

        if self._pages_fetched >= self.budget.max_pages:
            raise RuntimeError("fetcher violated successful-page budget")

        if self._bytes_fetched + byte_count > self.budget.max_total_bytes:
            raise RuntimeError("fetcher violated total byte budget")

        self._pages_fetched += 1
        self._bytes_fetched += byte_count

    @property
    def remaining_fetch_attempts(self) -> int:
        return max(
            0,
            self.budget.max_fetch_attempts - self._fetch_attempts,
        )

    @property
    def remaining_pages(self) -> int:
        return max(
            0,
            self.budget.max_pages - self._pages_fetched,
        )

    @property
    def remaining_bytes(self) -> int:
        return max(
            0,
            self.budget.max_total_bytes - self._bytes_fetched,
        )

    @property
    def search_exhausted(self) -> bool:
        return self._search_requests >= self.budget.max_searches

    @property
    def fetch_exhausted(self) -> bool:
        return (
            self.remaining_fetch_attempts == 0
            or self.remaining_pages == 0
            or self.remaining_bytes == 0
        )

    def usage(self) -> ResearchUsage:
        return ResearchUsage(
            search_requests=self._search_requests,
            fetch_attempts=self._fetch_attempts,
            pages_fetched=self._pages_fetched,
            bytes_fetched=self._bytes_fetched,
        )
