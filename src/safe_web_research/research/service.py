from safe_web_research.domain import (
    EvidenceBundle,
    ResearchRequest,
    ResearchResult,
    ResearchUsage,
)
from safe_web_research.research.gatherer import (
    EvidenceGatherer,
)
from safe_web_research.research.llm_budget import (
    LLMBudgetTracker,
)
from safe_web_research.research.planner import (
    ResearchPlanner,
)
from safe_web_research.research.synthesizer import (
    ResearchSynthesizer,
)

_PLANNER_OUTPUT_TOKEN_CAP = 1_000
_SYNTHESIS_OUTPUT_TOKEN_CAP = 4_000


class ResearchService:
    """Trusted orchestrator for bounded planning, gathering, and synthesis."""

    def __init__(
        self,
        planner: ResearchPlanner,
        gatherer: EvidenceGatherer,
        synthesizer: ResearchSynthesizer,
    ) -> None:
        self._planner = planner
        self._gatherer = gatherer
        self._synthesizer = synthesizer

    async def research(
        self,
        request: ResearchRequest,
    ) -> ResearchResult:
        llm_budget = LLMBudgetTracker(request.budget)

        orchestration_reasons: list[str] = []

        if request.budget.max_searches == 0:
            return self._empty_result(
                reason="max_searches_reached",
                llm_usage=llm_budget.usage(),
            )

        if request.budget.max_pages == 0 or request.budget.max_total_bytes == 0:
            return self._empty_result(
                reason="max_pages_reached",
                llm_usage=llm_budget.usage(),
            )

        planner_token_limit: int | None = None

        if (
            llm_budget.remaining_calls >= 2
            and llm_budget.remaining_output_tokens >= 2
            and llm_budget.remaining_input_tokens > 0
        ):
            planner_token_limit = llm_budget.reserve_call(
                min(
                    _PLANNER_OUTPUT_TOKEN_CAP,
                    max(
                        1,
                        llm_budget.remaining_output_tokens // 4,
                    ),
                )
            )

        if planner_token_limit is None:
            queries = [request.question]

            orchestration_reasons.append("planner_skipped_llm_budget")

        else:
            planning = await self._planner.plan(
                request,
                max_output_tokens=(planner_token_limit),
            )

            llm_budget.record_usage(planning.usage)

            queries = planning.plan.queries

        evidence_bundle = await self._gatherer.gather(
            request,
            queries=queries,
        )

        if not evidence_bundle.evidence:
            reasons = self._merge_reasons(
                evidence_bundle.incomplete_reasons,
                orchestration_reasons,
                ["no_evidence"],
            )

            return ResearchResult(
                answer="",
                sources=evidence_bundle.sources,
                evidence=evidence_bundle.evidence,
                security_events=(evidence_bundle.security_events),
                usage=self._merge_usage(
                    evidence_bundle.usage,
                    llm_budget.usage(),
                ),
                incomplete_reasons=reasons,
            )

        if llm_budget.input_budget_exhausted:
            orchestration_reasons.append("max_input_tokens_reached")

            return self._result_without_synthesis(
                evidence_bundle,
                llm_budget=llm_budget,
                orchestration_reasons=(orchestration_reasons),
            )

        synthesis_token_limit = llm_budget.reserve_call(_SYNTHESIS_OUTPUT_TOKEN_CAP)

        if synthesis_token_limit is None:
            orchestration_reasons.append("synthesis_skipped_llm_budget")

            return self._result_without_synthesis(
                evidence_bundle,
                llm_budget=llm_budget,
                orchestration_reasons=(orchestration_reasons),
            )

        synthesis = await self._synthesizer.synthesize(
            request,
            evidence_bundle,
            max_output_tokens=(synthesis_token_limit),
        )

        llm_budget.record_usage(synthesis.usage)

        if llm_budget.input_budget_exhausted:
            orchestration_reasons.append("max_input_tokens_reached")

        return ResearchResult(
            answer=synthesis.draft.answer,
            claims=synthesis.draft.claims,
            sources=evidence_bundle.sources,
            evidence=evidence_bundle.evidence,
            conflicts=(synthesis.draft.conflicts),
            security_events=(evidence_bundle.security_events),
            usage=self._merge_usage(
                evidence_bundle.usage,
                llm_budget.usage(),
            ),
            incomplete_reasons=(
                self._merge_reasons(
                    evidence_bundle.incomplete_reasons,
                    orchestration_reasons,
                )
            ),
        )

    @staticmethod
    def _empty_result(
        *,
        reason: str,
        llm_usage: ResearchUsage,
    ) -> ResearchResult:
        return ResearchResult(
            answer="",
            usage=llm_usage,
            incomplete_reasons=[reason],
        )

    @classmethod
    def _result_without_synthesis(
        cls,
        evidence_bundle: EvidenceBundle,
        *,
        llm_budget: LLMBudgetTracker,
        orchestration_reasons: list[str],
    ) -> ResearchResult:
        return ResearchResult(
            answer="",
            sources=evidence_bundle.sources,
            evidence=evidence_bundle.evidence,
            security_events=(evidence_bundle.security_events),
            usage=cls._merge_usage(
                evidence_bundle.usage,
                llm_budget.usage(),
            ),
            incomplete_reasons=(
                cls._merge_reasons(
                    evidence_bundle.incomplete_reasons,
                    orchestration_reasons,
                )
            ),
        )

    @staticmethod
    def _merge_usage(
        evidence_usage: ResearchUsage,
        llm_usage: ResearchUsage,
    ) -> ResearchUsage:
        return ResearchUsage(
            search_requests=(evidence_usage.search_requests),
            fetch_attempts=(evidence_usage.fetch_attempts),
            pages_fetched=(evidence_usage.pages_fetched),
            bytes_fetched=(evidence_usage.bytes_fetched),
            llm_calls=(llm_usage.llm_calls),
            input_tokens=(llm_usage.input_tokens),
            output_tokens=(llm_usage.output_tokens),
            estimated_cost_usd=(llm_usage.estimated_cost_usd),
        )

    @staticmethod
    def _merge_reasons(
        *groups: list[str],
    ) -> list[str]:
        result: list[str] = []

        for group in groups:
            for reason in group:
                if reason not in result:
                    result.append(reason)

        return result
