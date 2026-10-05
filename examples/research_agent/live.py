from __future__ import annotations

from enum import StrEnum
from time import perf_counter

from examples.research_agent.agent import ResearchAgent
from examples.research_agent.models import (
    AgentDecision,
    ClaimObservation,
    FetchCallObservation,
    JudgementCallObservation,
    ResearchCapability,
    ResearchLLMCallObservation,
    ResearchObservation,
    ResearchToolCall,
    SearchCallObservation,
    SourceObservation,
)
from safe_web_research.domain import (
    Claim,
    FetchedDocument,
    FetchRequest,
    LLMRequest,
    LLMResponse,
    ResearchBudget,
    ResearchRequest,
    SearchRequest,
    SearchResult,
)
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import Fetcher, SafeFetcher, SystemDNSResolver, URLPolicy
from safe_web_research.llm import LLMProvider, OpenRouterLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    EvidenceSelectionPolicy,
    EvidenceSelector,
    ResearchError,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import BraveSearchProvider, SearchProvider
from safe_web_research.security import (
    ContentJudgementMode,
    ContentJudgementObserver,
    ContentJudgementPolicy,
    ContentSecurityJudge,
    SecurityAssessment,
    SecurityJudgementInput,
)
from safe_web_research.security.openrouter_jev import (
    DEFAULT_JEV_MODEL,
    OpenRouterJevSecurityJudge,
)


class AgentResearchProfile(StrEnum):
    """Evidence sizing profile for the standalone agent experiment."""

    COMPACT = "compact"
    FULL = "full"


COMPACT_AGENT_RESEARCH_BUDGET = ResearchBudget(
    max_searches=4,
    max_fetch_attempts=8,
    max_pages=4,
    max_bytes_per_page=1_000_000,
    max_total_bytes=3_000_000,
    max_redirects=4,
    max_llm_calls=3,
    max_input_tokens=40_000,
    max_output_tokens=8_000,
)

FULL_AGENT_RESEARCH_BUDGET = ResearchBudget(
    max_searches=4,
    max_fetch_attempts=12,
    max_pages=6,
    max_bytes_per_page=2_000_000,
    max_total_bytes=8_000_000,
    max_redirects=4,
    max_llm_calls=3,
    max_input_tokens=150_000,
    max_output_tokens=20_000,
)

DEFAULT_AGENT_RESEARCH_BUDGET = COMPACT_AGENT_RESEARCH_BUDGET

_COMPACT_EVIDENCE_POLICY = EvidenceSelectionPolicy(
    max_selected_chars=30_000,
    max_chunks_per_source=4,
    min_sources_for_sufficiency=2,
    min_relevant_chunks_for_sufficiency=4,
    target_selected_chars=12_000,
    min_question_term_coverage=0.5,
)
_COMPACT_SYNTHESIS_EVIDENCE_CHARS = 30_000
_COMPACT_VERIFICATION_EVIDENCE_CHARS = 60_000
_COMPACT_EXTRACTOR_CHUNK_CHARS = 2_500


_AGENT_OBSERVATION_ANSWER_CHARS = 12_000
_AGENT_OBSERVATION_CLAIM_CHARS = 1_000
_AGENT_OBSERVATION_TITLE_CHARS = 500
_AGENT_OBSERVATION_MAX_SOURCES = 12
_AGENT_OBSERVATION_MAX_CLAIMS = 12


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    suffix = "\n[truncated for outer-agent context]"
    keep = max(0, limit - len(suffix))
    return value[:keep] + suffix


class TracingSearchProvider:
    """Record bounded diagnostics for every real search-provider call."""

    def __init__(self, delegate: SearchProvider) -> None:
        self._delegate = delegate
        self._calls: list[SearchCallObservation] = []

    def mark(self) -> int:
        return len(self._calls)

    def calls_since(self, mark: int) -> list[SearchCallObservation]:
        return list(self._calls[mark:])

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        started = perf_counter()
        try:
            results = await self._delegate.search(request)
        except Exception as exc:
            self._calls.append(
                SearchCallObservation(
                    query=_clip_text(request.query, 2_000),
                    domains=list(request.include_domains),
                    freshness_days=request.freshness_days,
                    language=request.language,
                    country=request.country,
                    seconds=perf_counter() - started,
                    ok=False,
                    result_count=0,
                    error_type=type(exc).__name__,
                    error_message=_clip_text(str(exc), 1_000),
                )
            )
            raise

        self._calls.append(
            SearchCallObservation(
                query=_clip_text(request.query, 2_000),
                domains=list(request.include_domains),
                freshness_days=request.freshness_days,
                language=request.language,
                country=request.country,
                seconds=perf_counter() - started,
                ok=True,
                result_count=len(results),
            )
        )
        return results


class TracingFetcher:
    """Record latency and outcome for each SSRF-safe page fetch."""

    def __init__(self, delegate: Fetcher) -> None:
        self._delegate = delegate
        self._calls: list[FetchCallObservation] = []

    def mark(self) -> int:
        return len(self._calls)

    def calls_since(self, mark: int) -> list[FetchCallObservation]:
        return list(self._calls[mark:])

    async def fetch(self, request: FetchRequest) -> FetchedDocument:
        started = perf_counter()
        try:
            document = await self._delegate.fetch(request)
        except Exception as exc:
            self._calls.append(
                FetchCallObservation(
                    url=_clip_text(str(request.url), 4_000),
                    seconds=perf_counter() - started,
                    ok=False,
                    bytes_fetched=0,
                    error_type=type(exc).__name__,
                    error_message=_clip_text(str(exc), 1_000),
                )
            )
            raise

        self._calls.append(
            FetchCallObservation(
                url=_clip_text(str(request.url), 4_000),
                seconds=perf_counter() - started,
                ok=True,
                bytes_fetched=len(document.body),
            )
        )
        return document


class TracingLLMProvider:
    """Record latency for the inner research planner/synthesizer/verifier calls."""

    def __init__(self, delegate: LLMProvider) -> None:
        self._delegate = delegate
        self._calls: list[ResearchLLMCallObservation] = []

    def mark(self) -> int:
        return len(self._calls)

    def calls_since(self, mark: int) -> list[ResearchLLMCallObservation]:
        return list(self._calls[mark:])

    async def complete(self, request: LLMRequest) -> LLMResponse:
        started = perf_counter()
        purpose = request.response_schema_name or "unstructured"
        try:
            response = await self._delegate.complete(request)
        except Exception as exc:
            self._calls.append(
                ResearchLLMCallObservation(
                    purpose=_clip_text(purpose, 100),
                    seconds=perf_counter() - started,
                    ok=False,
                    error_type=type(exc).__name__,
                    error_message=_clip_text(str(exc), 1_000),
                )
            )
            raise

        self._calls.append(
            ResearchLLMCallObservation(
                purpose=_clip_text(purpose, 100),
                seconds=perf_counter() - started,
                ok=True,
                model=_clip_text(response.model, 500),
                usage=response.usage,
            )
        )
        return response


class TracingContentSecurityJudge:
    """Record latency for each Jev semantic judgement call."""

    def __init__(self, delegate: ContentSecurityJudge) -> None:
        self._delegate = delegate
        self._calls: list[JudgementCallObservation] = []

    def mark(self) -> int:
        return len(self._calls)

    def calls_since(self, mark: int) -> list[JudgementCallObservation]:
        return list(self._calls[mark:])

    async def assess(self, content: SecurityJudgementInput) -> SecurityAssessment:
        started = perf_counter()
        try:
            assessment = await self._delegate.assess(content)
        except Exception as exc:
            self._calls.append(
                JudgementCallObservation(
                    source_url=_clip_text(content.source_url, 4_000),
                    seconds=perf_counter() - started,
                    ok=False,
                    error_type=type(exc).__name__,
                    error_message=_clip_text(str(exc), 1_000),
                )
            )
            raise

        self._calls.append(
            JudgementCallObservation(
                source_url=_clip_text(content.source_url, 4_000),
                seconds=perf_counter() - started,
                ok=True,
                model=_clip_text(assessment.model, 500),
                input_tokens=assessment.usage.input_tokens,
                output_tokens=assessment.usage.output_tokens,
                cost_usd=assessment.usage.estimated_cost_usd,
            )
        )
        return assessment


class SafeWebResearchTool:
    """Trusted adapter from an agent decision to a bounded ResearchRequest."""

    def __init__(
        self,
        service: ResearchService,
        *,
        budget: ResearchBudget = DEFAULT_AGENT_RESEARCH_BUDGET,
        search_trace: TracingSearchProvider | None = None,
        fetch_trace: TracingFetcher | None = None,
        llm_trace: TracingLLMProvider | None = None,
        judgement_trace: TracingContentSecurityJudge | None = None,
    ) -> None:
        self._service = service
        self._budget = budget
        self._search_trace = search_trace
        self._fetch_trace = fetch_trace
        self._llm_trace = llm_trace
        self._judgement_trace = judgement_trace

    def build_request(self, decision: AgentDecision) -> ResearchRequest:
        if decision.action != "research":
            raise ValueError("safe_web_research requires a research decision")
        question = (decision.question or "").strip()
        if not question:
            raise ValueError("research decision requires a non-empty question")
        if decision.capability is None:
            raise ValueError("research decision requires a capability")

        domains = [item.strip() for item in decision.domains if item.strip()]
        if len(domains) != len(decision.domains):
            raise ValueError("domains must not contain empty values")

        freshness_days: int | None = None
        language: str | None = None
        country: str | None = None

        if decision.capability is ResearchCapability.OPEN_WEB:
            if domains or decision.freshness_days or decision.language or decision.country:
                raise ValueError(
                    "open_web does not accept domain, freshness, or locale constraints"
                )
        elif decision.capability is ResearchCapability.OFFICIAL_SOURCES:
            if not domains:
                raise ValueError("official_sources requires at least one domain")
            if decision.freshness_days or decision.language or decision.country:
                raise ValueError("official_sources accepts domains only")
        elif decision.capability is ResearchCapability.RECENT_WEB:
            if decision.freshness_days is None:
                raise ValueError("recent_web requires freshness_days")
            if decision.language or decision.country:
                raise ValueError("recent_web does not accept locale constraints")
            freshness_days = decision.freshness_days
        elif decision.capability is ResearchCapability.REGIONAL_WEB:
            if not decision.language or not decision.country:
                raise ValueError("regional_web requires language and country")
            if decision.freshness_days is not None:
                raise ValueError("regional_web does not accept freshness_days")
            language = decision.language
            country = decision.country
        else:
            raise ValueError(f"unsupported research capability: {decision.capability}")

        return ResearchRequest(
            question=question,
            budget=self._budget.model_copy(deep=True),
            allowed_domains=domains,
            freshness_days=freshness_days,
            language=language,
            country=country,
        )

    async def run(self, decision: AgentDecision, *, step: int) -> ResearchToolCall:
        capability = decision.capability or ResearchCapability.OPEN_WEB
        question = (decision.question or "").strip()
        started = perf_counter()
        search_mark = self._search_trace.mark() if self._search_trace is not None else 0
        fetch_mark = self._fetch_trace.mark() if self._fetch_trace is not None else 0
        llm_mark = self._llm_trace.mark() if self._llm_trace is not None else 0
        judgement_mark = self._judgement_trace.mark() if self._judgement_trace is not None else 0

        def trace_fields() -> dict[str, object]:
            return {
                "search_calls": (
                    self._search_trace.calls_since(search_mark)
                    if self._search_trace is not None
                    else []
                ),
                "fetch_calls": (
                    self._fetch_trace.calls_since(fetch_mark)
                    if self._fetch_trace is not None
                    else []
                ),
                "research_llm_calls": (
                    self._llm_trace.calls_since(llm_mark) if self._llm_trace is not None else []
                ),
                "judgement_calls": (
                    self._judgement_trace.calls_since(judgement_mark)
                    if self._judgement_trace is not None
                    else []
                ),
            }

        try:
            request = self.build_request(decision)
        except ValueError as exc:
            return ResearchToolCall(
                step=step,
                capability=capability,
                question=question,
                domains=list(decision.domains),
                freshness_days=decision.freshness_days,
                language=decision.language,
                country=decision.country,
                seconds=perf_counter() - started,
                ok=False,
                error=str(exc),
                **trace_fields(),
            )

        try:
            result = await self._service.research(request)
        except ResearchError as exc:
            return ResearchToolCall(
                step=step,
                capability=request_capability(decision),
                question=request.question,
                domains=request.allowed_domains,
                freshness_days=request.freshness_days,
                language=request.language,
                country=request.country,
                seconds=perf_counter() - started,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                **trace_fields(),
            )
        elapsed = perf_counter() - started
        verdicts = {item.claim_id: item.verdict.value for item in result.claim_verifications}
        verification_support = {
            item.claim_id: item.supporting_evidence_ids for item in result.claim_verifications
        }
        clipped_answer = _clip_text(result.answer, _AGENT_OBSERVATION_ANSWER_CHARS)
        source_slice = result.sources[:_AGENT_OBSERVATION_MAX_SOURCES]
        claim_slice = result.claims[:_AGENT_OBSERVATION_MAX_CLAIMS]
        source_urls_by_id = {source.source_id: str(source.url) for source in source_slice}
        evidence_source_ids = {chunk.chunk_id: chunk.source_id for chunk in result.evidence}

        def claim_source_urls(claim: Claim) -> list[str]:
            evidence_ids = verification_support.get(claim.claim_id, claim.evidence_ids)
            urls: list[str] = []
            seen: set[str] = set()
            for evidence_id in evidence_ids:
                source_id = evidence_source_ids.get(evidence_id)
                url = source_urls_by_id.get(source_id or "")
                if url is None or url in seen:
                    continue
                seen.add(url)
                urls.append(url)
                if len(urls) == 8:
                    break
            return urls

        observation = ResearchObservation(
            answer=clipped_answer,
            sources=[
                SourceObservation(
                    title=_clip_text(source.title, _AGENT_OBSERVATION_TITLE_CHARS),
                    url=str(source.url),
                )
                for source in source_slice
            ],
            claims=[
                ClaimObservation(
                    claim_id=_clip_text(claim.claim_id, 200),
                    text=_clip_text(claim.text, _AGENT_OBSERVATION_CLAIM_CHARS),
                    verdict=verdicts.get(claim.claim_id),
                    source_urls=claim_source_urls(claim),
                )
                for claim in claim_slice
            ],
            incomplete_reasons=result.incomplete_reasons[:20],
            security_event_count=len(result.security_events),
            usage=result.usage,
            answer_chars_original=len(result.answer),
            sources_total=len(result.sources),
            claims_total=len(result.claims),
            observation_truncated=(
                len(result.answer) > len(clipped_answer)
                or len(result.sources) > len(source_slice)
                or len(result.claims) > len(claim_slice)
                or any(len(claim.text) > _AGENT_OBSERVATION_CLAIM_CHARS for claim in claim_slice)
                or any(
                    len(source.title) > _AGENT_OBSERVATION_TITLE_CHARS for source in source_slice
                )
            ),
        )
        return ResearchToolCall(
            step=step,
            capability=request_capability(decision),
            question=request.question,
            domains=request.allowed_domains,
            freshness_days=request.freshness_days,
            language=request.language,
            country=request.country,
            seconds=elapsed,
            ok=True,
            observation=observation,
            **trace_fields(),
        )


def request_capability(decision: AgentDecision) -> ResearchCapability:
    if decision.capability is None:
        raise ValueError("research decision requires a capability")
    return decision.capability


def build_live_agent(
    *,
    brave_api_key: str,
    openrouter_api_key: str,
    agent_model: str,
    research_model: str,
    max_steps: int = 6,
    max_tool_calls: int = 4,
    verify: bool = True,
    content_judgement_mode: ContentJudgementMode = ContentJudgementMode.OBSERVE,
    jev_model: str = DEFAULT_JEV_MODEL,
    research_profile: AgentResearchProfile = AgentResearchProfile.COMPACT,
    budget: ResearchBudget | None = None,
) -> ResearchAgent:
    research_llm_trace = TracingLLMProvider(
        OpenRouterLLMProvider(
            openrouter_api_key,
            model=research_model,
            app_title="safe-web-research agent example / research",
        )
    )
    outer_llm = OpenRouterLLMProvider(
        openrouter_api_key,
        model=agent_model,
        app_title="safe-web-research agent example / outer agent",
    )

    judgement_trace: TracingContentSecurityJudge | None = None
    content_judgement = ContentJudgementObserver()
    if content_judgement_mode is ContentJudgementMode.OBSERVE:
        judgement_trace = TracingContentSecurityJudge(
            OpenRouterJevSecurityJudge(
                openrouter_api_key,
                model=jev_model,
                app_title="safe-web-research agent example / Jev",
            )
        )
        content_judgement = ContentJudgementObserver(
            judgement_trace,
            policy=ContentJudgementPolicy(mode=ContentJudgementMode.OBSERVE),
        )

    if research_profile is AgentResearchProfile.COMPACT:
        selected_budget = budget or COMPACT_AGENT_RESEARCH_BUDGET
        extractor = WebExtractor(max_chunk_chars=_COMPACT_EXTRACTOR_CHUNK_CHARS)
        evidence_selector = EvidenceSelector(_COMPACT_EVIDENCE_POLICY)
        synthesizer = ResearchSynthesizer(
            research_llm_trace,
            max_evidence_chars=_COMPACT_SYNTHESIS_EVIDENCE_CHARS,
        )
        verifier = (
            ResearchVerifier(
                research_llm_trace,
                max_evidence_chars=_COMPACT_VERIFICATION_EVIDENCE_CHARS,
            )
            if verify
            else None
        )
    else:
        selected_budget = budget or FULL_AGENT_RESEARCH_BUDGET
        extractor = WebExtractor()
        evidence_selector = EvidenceSelector()
        synthesizer = ResearchSynthesizer(research_llm_trace)
        verifier = ResearchVerifier(research_llm_trace) if verify else None

    search_trace = TracingSearchProvider(BraveSearchProvider(brave_api_key))
    fetch_trace = TracingFetcher(SafeFetcher(URLPolicy(SystemDNSResolver())))
    service = ResearchService(
        ResearchPlanner(research_llm_trace),
        EvidenceGatherer(
            search_trace,
            fetch_trace,
            extractor,
            evidence_selector=evidence_selector,
            content_judgement=content_judgement,
        ),
        synthesizer,
        verifier,
    )
    return ResearchAgent(
        outer_llm,
        SafeWebResearchTool(
            service,
            budget=selected_budget,
            search_trace=search_trace,
            fetch_trace=fetch_trace,
            llm_trace=research_llm_trace,
            judgement_trace=judgement_trace,
        ),
        agent_model=agent_model,
        research_model=research_model,
        max_steps=max_steps,
        max_tool_calls=max_tool_calls,
    )
