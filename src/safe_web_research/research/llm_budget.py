from dataclasses import dataclass

from safe_web_research.domain.llm import LLMUsage
from safe_web_research.domain.usage import ResearchBudget, ResearchUsage
from safe_web_research.research.errors import ResearchBudgetError


@dataclass(slots=True)
class LLMBudgetTracker:
    """Track and bound language-model calls and generated tokens."""

    budget: ResearchBudget

    _llm_calls: int = 0
    _input_tokens: int = 0
    _output_tokens: int = 0
    _estimated_cost_usd: float = 0.0

    @property
    def remaining_calls(self) -> int:
        return max(
            0,
            self.budget.max_llm_calls - self._llm_calls,
        )

    @property
    def remaining_input_tokens(self) -> int:
        return max(
            0,
            self.budget.max_input_tokens - self._input_tokens,
        )

    @property
    def remaining_output_tokens(self) -> int:
        return max(
            0,
            self.budget.max_output_tokens - self._output_tokens,
        )

    def reserve_call(
        self,
        requested_output_tokens: int,
    ) -> int | None:
        if requested_output_tokens <= 0:
            raise ValueError("requested_output_tokens must be greater than zero")

        if self.remaining_calls == 0 or self.remaining_output_tokens == 0:
            return None

        if self.remaining_input_tokens == 0:
            return None

        self._llm_calls += 1

        return min(
            requested_output_tokens,
            self.remaining_output_tokens,
        )

    def record_usage(
        self,
        usage: LLMUsage,
    ) -> None:
        new_input_tokens = self._input_tokens + usage.input_tokens

        new_output_tokens = self._output_tokens + usage.output_tokens

        if new_output_tokens > self.budget.max_output_tokens:
            raise ResearchBudgetError("LLM provider exceeded the configured output-token budget")

        self._input_tokens = new_input_tokens
        self._output_tokens = new_output_tokens

        self._estimated_cost_usd += usage.estimated_cost_usd

    @property
    def input_budget_exhausted(self) -> bool:
        return self._input_tokens >= self.budget.max_input_tokens

    def usage(self) -> ResearchUsage:
        return ResearchUsage(
            llm_calls=self._llm_calls,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            estimated_cost_usd=self._estimated_cost_usd,
        )
