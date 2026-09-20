from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoppingPolicy:
    """Deterministic stopping policy for evidence gathering."""

    max_consecutive_empty_queries: int = 2

    def __post_init__(self) -> None:
        if self.max_consecutive_empty_queries <= 0:
            raise ValueError("max_consecutive_empty_queries must be greater than zero")

    def should_stop(
        self,
        consecutive_empty_queries: int,
    ) -> bool:
        return consecutive_empty_queries >= self.max_consecutive_empty_queries
