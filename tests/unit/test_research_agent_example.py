import json
from types import SimpleNamespace

import pytest

from benchmarks.agent_usage.models import AgentUsageCase, AgentUsageSuite
from benchmarks.agent_usage.runner import evaluate_case, run_suite
from examples.research_agent.agent import ResearchAgent
from examples.research_agent.live import SafeWebResearchTool, TracingSearchProvider
from examples.research_agent.models import (
    AgentDecision,
    ClaimObservation,
    ResearchCapability,
    ResearchObservation,
    ResearchToolCall,
    SourceObservation,
)
from safe_web_research.domain import (
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ResearchUsage,
    SearchRequest,
)
from safe_web_research.llm import LLMStructuredOutputError
from safe_web_research.search import SearchProviderRequestError


class ScriptedLLM:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        self.requests.append(request)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        content = json.dumps(item) if request.response_schema is not None else str(item)
        return LLMResponse(
            content=content,
            model="test/outer",
            usage=LLMUsage(
                input_tokens=10,
                output_tokens=5,
                estimated_cost_usd=0.001,
            ),
        )


class ScriptedResearchTool:
    def __init__(self) -> None:
        self.decisions: list[AgentDecision] = []

    async def run(self, decision: AgentDecision, *, step: int) -> ResearchToolCall:
        self.decisions.append(decision)
        return ResearchToolCall(
            step=step,
            capability=decision.capability or ResearchCapability.OPEN_WEB,
            question=decision.question or "",
            domains=list(decision.domains),
            freshness_days=decision.freshness_days,
            language=decision.language,
            country=decision.country,
            seconds=0.01,
            ok=True,
            observation=ResearchObservation(
                answer="TaskGroup aggregates failures.",
                sources=[
                    SourceObservation(
                        title="Python docs",
                        url="https://docs.python.org/3/library/asyncio-task.html",
                    )
                ],
                claims=[
                    ClaimObservation(
                        claim_id="claim-1",
                        text="TaskGroup aggregates failures.",
                        verdict="supported",
                    )
                ],
                incomplete_reasons=[],
                security_event_count=0,
                usage=ResearchUsage(
                    search_requests=2,
                    fetch_attempts=3,
                    pages_fetched=1,
                    llm_calls=3,
                    input_tokens=100,
                    output_tokens=20,
                    judgement_calls=1,
                    judgement_input_tokens=50,
                    judgement_output_tokens=2,
                    judgement_cost_usd=0.002,
                    estimated_cost_usd=0.020,
                ),
                answer_chars_original=30,
                sources_total=1,
                claims_total=1,
                observation_truncated=False,
            ),
        )


class LargeResultService:
    async def research(self, request: object) -> object:
        del request
        return SimpleNamespace(
            answer="a" * 20_000,
            sources=[
                SimpleNamespace(
                    source_id=f"source-{index}",
                    title="t" * 700,
                    url=f"https://example.com/source-{index}",
                )
                for index in range(14)
            ],
            evidence=[
                SimpleNamespace(chunk_id=f"evidence-{index}", source_id=f"source-{index}")
                for index in range(14)
            ],
            claims=[
                SimpleNamespace(
                    claim_id=f"claim-{index}",
                    text="c" * 2_000,
                    evidence_ids=[f"evidence-{index}"],
                )
                for index in range(14)
            ],
            claim_verifications=[],
            incomplete_reasons=[],
            security_events=[],
            usage=ResearchUsage(search_requests=1),
        )


def _decision(
    capability: ResearchCapability,
    *,
    domains: list[str] | None = None,
    freshness_days: int | None = None,
    language: str | None = None,
    country: str | None = None,
) -> AgentDecision:
    return AgentDecision(
        action="research",
        question="test question",
        capability=capability,
        domains=domains or [],
        freshness_days=freshness_days,
        language=language,
        country=country,
    )


def _finish_decision() -> dict[str, object]:
    return {
        "action": "finish",
        "question": None,
        "capability": None,
        "domains": [],
        "freshness_days": None,
        "language": None,
        "country": None,
    }


def test_agent_decision_schema_is_small_and_requires_explicit_nulls() -> None:
    schema = AgentDecision.model_json_schema()
    assert set(schema["required"]) == {
        "action",
        "question",
        "capability",
        "domains",
        "freshness_days",
        "language",
        "country",
    }
    assert "answer" not in schema["properties"]
    question_variants = schema["properties"]["question"]["anyOf"]
    string_variant = next(item for item in question_variants if item.get("type") == "string")
    assert string_variant["maxLength"] == 1_000


class FailingSearchProvider:
    async def search(self, request: SearchRequest) -> list[object]:
        del request
        raise SearchProviderRequestError("provider rejected generated query")


@pytest.mark.asyncio
async def test_search_trace_records_provider_error_before_it_is_absorbed_by_research() -> None:
    traced = TracingSearchProvider(FailingSearchProvider())  # type: ignore[arg-type]
    mark = traced.mark()

    with pytest.raises(SearchProviderRequestError, match="rejected generated query"):
        await traced.search(SearchRequest(query="generated search query"))

    calls = traced.calls_since(mark)
    assert len(calls) == 1
    assert calls[0].query == "generated search query"
    assert not calls[0].ok
    assert calls[0].result_count == 0
    assert calls[0].error_type == "SearchProviderRequestError"
    assert "rejected generated query" in (calls[0].error_message or "")


def test_safe_web_research_tool_maps_capabilities_to_research_request() -> None:
    tool = SafeWebResearchTool(object())  # type: ignore[arg-type]

    open_request = tool.build_request(_decision(ResearchCapability.OPEN_WEB))
    assert open_request.allowed_domains == []
    assert open_request.freshness_days is None

    official = tool.build_request(
        _decision(ResearchCapability.OFFICIAL_SOURCES, domains=["python.org"])
    )
    assert official.allowed_domains == ["python.org"]

    recent = tool.build_request(_decision(ResearchCapability.RECENT_WEB, freshness_days=14))
    assert recent.freshness_days == 14

    regional = tool.build_request(
        _decision(ResearchCapability.REGIONAL_WEB, language="de", country="DE")
    )
    assert regional.language == "de"
    assert regional.country == "DE"


def test_safe_web_research_tool_rejects_constraints_outside_profile() -> None:
    tool = SafeWebResearchTool(object())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="open_web"):
        tool.build_request(_decision(ResearchCapability.OPEN_WEB, domains=["example.com"]))

    with pytest.raises(ValueError, match="requires at least one domain"):
        tool.build_request(_decision(ResearchCapability.OFFICIAL_SOURCES))

    with pytest.raises(ValueError, match="requires freshness_days"):
        tool.build_request(_decision(ResearchCapability.RECENT_WEB))

    with pytest.raises(ValueError, match="requires language and country"):
        tool.build_request(_decision(ResearchCapability.REGIONAL_WEB, language="de"))


@pytest.mark.asyncio
async def test_tool_compacts_large_research_result_before_outer_agent_context() -> None:
    tool = SafeWebResearchTool(LargeResultService())  # type: ignore[arg-type]

    call = await tool.run(_decision(ResearchCapability.OPEN_WEB), step=1)

    assert call.ok
    assert call.observation is not None
    assert len(call.observation.answer) == 12_000
    assert len(call.observation.sources) == 12
    assert len(call.observation.claims) == 12
    assert max(len(item.title) for item in call.observation.sources) == 500
    assert max(len(item.text) for item in call.observation.claims) == 1_000
    assert call.observation.claims[0].source_urls == ["https://example.com/source-0"]
    assert call.observation.claims[-1].source_urls == ["https://example.com/source-11"]
    assert call.observation.answer_chars_original == 20_000
    assert call.observation.sources_total == 14
    assert call.observation.claims_total == 14
    assert call.observation.observation_truncated


@pytest.mark.asyncio
async def test_agent_calls_bounded_tool_then_uses_plain_text_finalizer_and_accounts_usage() -> None:
    llm = ScriptedLLM(
        [
            {
                "action": "research",
                "question": "TaskGroup child failure behavior",
                "capability": "official_sources",
                "domains": ["python.org"],
                "freshness_days": None,
                "language": None,
                "country": None,
            },
            _finish_decision(),
            ("TaskGroup aggregates failures. https://docs.python.org/3/library/asyncio-task.html"),
        ]
    )
    tool = ScriptedResearchTool()
    agent = ResearchAgent(
        llm,
        tool,
        agent_model="test/outer",
        research_model="test/research",
    )

    run = await agent.run("Explain TaskGroup from official Python docs.")

    assert run.error_type is None
    assert run.final_answer.startswith("TaskGroup")
    assert [call.capability for call in run.tool_calls] == [ResearchCapability.OFFICIAL_SOURCES]
    assert [call.purpose for call in run.model_calls] == [
        "decision",
        "decision",
        "final_answer",
    ]
    assert llm.requests[0].response_schema is not None
    assert llm.requests[0].max_output_tokens == 512
    assert llm.requests[2].response_schema is None
    assert llm.requests[2].max_output_tokens == 1_500
    assert run.search_requests == 2
    assert run.search_provider_errors == 0
    assert run.pages_fetched == 1
    assert run.agent_input_tokens == 30
    assert run.agent_output_tokens == 15
    assert run.research_input_tokens == 100
    assert run.research_output_tokens == 20
    assert run.agent_cost_usd == pytest.approx(0.003)
    assert run.research_cost_usd == pytest.approx(0.020)
    assert run.tracked_cost_usd == pytest.approx(0.023)
    assert run.time_to_first_research_result_seconds is not None


@pytest.mark.asyncio
async def test_agent_prevents_redundant_complete_same_scope_research_call() -> None:
    llm = ScriptedLLM(
        [
            {
                "action": "research",
                "question": "Python 3.15 developments",
                "capability": "recent_web",
                "domains": [],
                "freshness_days": 30,
                "language": None,
                "country": None,
            },
            {
                "action": "research",
                "question": "More Python 3.15 developments",
                "capability": "recent_web",
                "domains": [],
                "freshness_days": 30,
                "language": None,
                "country": None,
            },
            "Grounded answer https://docs.python.org/3/library/asyncio-task.html",
        ]
    )
    tool = ScriptedResearchTool()
    agent = ResearchAgent(
        llm,
        tool,
        agent_model="test/outer",
        research_model="test/research",
    )

    run = await agent.run("Research recent Python 3.15 developments.")

    assert run.error_type is None
    assert len(tool.decisions) == 1
    assert run.redundant_research_calls_prevented == 1
    assert [call.purpose for call in run.model_calls] == [
        "decision",
        "decision",
        "final_answer",
    ]


@pytest.mark.asyncio
async def test_agent_records_structured_output_failure_instead_of_raising() -> None:
    llm = ScriptedLLM([LLMStructuredOutputError("completion token limit was reached")])
    agent = ResearchAgent(
        llm,
        ScriptedResearchTool(),
        agent_model="test/outer",
        research_model="test/research",
    )

    run = await agent.run("Research something.")

    assert run.final_answer == ""
    assert run.error_type == "LLMStructuredOutputError"
    assert "token limit" in (run.error_message or "")
    assert run.failed_step == 1
    assert run.failed_purpose == "decision"


@pytest.mark.asyncio
async def test_agent_refuses_to_finish_before_successful_research() -> None:
    llm = ScriptedLLM(
        [
            _finish_decision(),
            {
                "action": "research",
                "question": "SSRF defenses",
                "capability": "open_web",
                "domains": [],
                "freshness_days": None,
                "language": None,
                "country": None,
            },
            _finish_decision(),
            "Grounded answer https://docs.python.org/3/library/asyncio-task.html",
        ]
    )
    tool = ScriptedResearchTool()
    agent = ResearchAgent(
        llm,
        tool,
        agent_model="test/outer",
        research_model="test/research",
    )

    run = await agent.run("Research SSRF defenses.")

    assert run.error_type is None
    assert llm.calls == 4
    assert len(tool.decisions) == 1
    assert run.final_answer.startswith("Grounded answer")


@pytest.mark.asyncio
async def test_case_evaluation_reports_exact_failed_checks() -> None:
    llm = ScriptedLLM(
        [
            {
                "action": "research",
                "question": "SSRF defenses",
                "capability": "open_web",
                "domains": [],
                "freshness_days": None,
                "language": None,
                "country": None,
            },
            _finish_decision(),
            "Grounded answer https://docs.python.org/3/library/asyncio-task.html",
        ]
    )
    agent = ResearchAgent(
        llm,
        ScriptedResearchTool(),
        agent_model="test/outer",
        research_model="test/research",
    )
    run = await agent.run("Research SSRF defenses.")
    case = AgentUsageCase(
        case_id="diagnostic",
        category="diagnostic",
        task="Research SSRF defenses.",
        expected_capabilities=[ResearchCapability.OPEN_WEB],
        expected_terms=["definitely-missing-term"],
    )

    result = evaluate_case(case, run)

    assert result.outcome == "fail"
    assert result.failed_checks == ["expected_terms"]


def test_finalizer_requires_distinct_claim_supporting_citations_for_comparison_tasks() -> None:
    messages = ResearchAgent._final_messages(
        "Compare at least two independent explanations with citations.",
        [
            ResearchToolCall(
                step=1,
                capability=ResearchCapability.OPEN_WEB,
                question="Compare two independent SSRF defense explanations.",
                domains=[],
                freshness_days=None,
                language=None,
                country=None,
                seconds=0.1,
                ok=True,
                observation=ResearchObservation(
                    answer="Two explanations agree on allowlists and redirect controls.",
                    sources=[
                        SourceObservation(title="One", url="https://one.example/ssrf"),
                        SourceObservation(title="Two", url="https://two.example/ssrf"),
                    ],
                    claims=[
                        ClaimObservation(
                            claim_id="claim-1",
                            text="Both recommend strict destination validation.",
                            verdict="supported",
                            source_urls=[
                                "https://one.example/ssrf",
                                "https://two.example/ssrf",
                            ],
                        )
                    ],
                    incomplete_reasons=[],
                    security_event_count=0,
                    usage=ResearchUsage(search_requests=1),
                    answer_chars_original=60,
                    sources_total=2,
                    claims_total=1,
                    observation_truncated=False,
                ),
            )
        ],
    )

    assert "cite at least two distinct URLs" in messages[0].content
    assert "Claim source_urls" in messages[0].content
    assert "https://one.example/ssrf" in messages[1].content
    assert "https://two.example/ssrf" in messages[1].content


@pytest.mark.asyncio
async def test_live_suite_records_one_agent_error_and_continues_to_next_case() -> None:
    llm = ScriptedLLM(
        [
            LLMStructuredOutputError("bad structured output"),
            {
                "action": "research",
                "question": "SSRF defenses",
                "capability": "open_web",
                "domains": [],
                "freshness_days": None,
                "language": None,
                "country": None,
            },
            _finish_decision(),
            "SSRF answer https://docs.python.org/3/library/asyncio-task.html",
        ]
    )
    agent = ResearchAgent(
        llm,
        ScriptedResearchTool(),
        agent_model="test/outer",
        research_model="test/research",
    )
    suite = AgentUsageSuite(
        cases=[
            AgentUsageCase(
                case_id="provider-error",
                category="resilience",
                task="first",
                expected_capabilities=[ResearchCapability.OPEN_WEB],
            ),
            AgentUsageCase(
                case_id="continues",
                category="resilience",
                task="second",
                expected_capabilities=[ResearchCapability.OPEN_WEB],
                expected_terms=["SSRF"],
            ),
        ]
    )

    run = await run_suite(
        suite,
        agent=agent,
        git_commit="deadbeef",
        git_dirty=True,
        case_file="cases.json",
        agent_model="test/outer",
        research_model="test/research",
        research_profile="compact",
    )

    assert run.total_cases == 2
    assert run.error_cases == 1
    assert run.cases[0].outcome == "error"
    assert run.cases[1].outcome == "pass"
