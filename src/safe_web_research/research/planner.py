import json
from dataclasses import dataclass

from pydantic import ValidationError

from safe_web_research.domain import (
    LLMMessage,
    LLMRequest,
    LLMRole,
    LLMUsage,
    ResearchPlan,
    ResearchRequest,
)
from safe_web_research.llm import (
    LLMProvider,
    LLMProviderError,
)
from safe_web_research.research.errors import (
    ResearchPlanningError,
)


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    plan: ResearchPlan
    usage: LLMUsage
    model: str


class ResearchPlanner:
    """Ask an LLM for a bounded list of search queries."""

    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        self._llm_provider = llm_provider

    async def plan(
        self,
        request: ResearchRequest,
        *,
        max_output_tokens: int,
    ) -> PlanningOutcome:
        max_queries = min(
            20,
            request.budget.max_searches,
        )

        if max_queries <= 0:
            raise ResearchPlanningError("Research request allows no search queries")

        schema = ResearchPlan.model_json_schema()

        properties = schema.get("properties")

        if isinstance(
            properties,
            dict,
        ):
            queries_schema = properties.get("queries")

            if isinstance(
                queries_schema,
                dict,
            ):
                queries_schema["maxItems"] = max_queries

        constraints = {
            "max_queries": max_queries,
            "allowed_domains": request.allowed_domains,
            "blocked_domains": request.blocked_domains,
            "freshness_days": request.freshness_days,
            "language": request.language,
            "country": request.country,
        }

        llm_request = LLMRequest(
            messages=[
                LLMMessage(
                    role=LLMRole.SYSTEM,
                    content=(
                        "You are a research planner. "
                        "Produce only search queries "
                        "needed to answer the user's "
                        "question. Do not answer the "
                        "question. Do not invent URLs. "
                        "Respect the supplied constraints. "
                        "Keep queries concise and "
                        "non-duplicative."
                    ),
                ),
                LLMMessage(
                    role=LLMRole.USER,
                    content=(
                        "Question:\n"
                        f"{request.question}\n\n"
                        "Constraints:\n"
                        f"{json.dumps(constraints, sort_keys=True)}"
                    ),
                ),
            ],
            response_schema=schema,
            response_schema_name=("research_plan"),
            max_output_tokens=max_output_tokens,
        )

        try:
            response = await self._llm_provider.complete(llm_request)

        except LLMProviderError as exc:
            raise ResearchPlanningError("Research planner LLM call failed") from exc

        try:
            plan = ResearchPlan.model_validate_json(response.content)

        except ValidationError as exc:
            raise ResearchPlanningError("Research planner returned an invalid plan") from exc

        normalized_queries: list[str] = []
        seen: set[str] = set()

        for query in plan.queries:
            normalized = " ".join(query.split())

            if not normalized:
                continue

            key = normalized.casefold()

            if key in seen:
                continue

            seen.add(key)

            normalized_queries.append(normalized)

        if not normalized_queries:
            raise ResearchPlanningError("Research planner returned no usable queries")

        if len(normalized_queries) > max_queries:
            raise ResearchPlanningError("Research planner exceeded the search-query budget")

        return PlanningOutcome(
            plan=ResearchPlan(queries=normalized_queries),
            usage=response.usage,
            model=response.model,
        )
