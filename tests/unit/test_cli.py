import json

import pytest

from safe_web_research import cli
from safe_web_research.domain import (
    Claim,
    ClaimSupport,
    ClaimVerification,
    ResearchResult,
    ResearchUsage,
)
from safe_web_research.security import ContentJudgementMode


class _FakeService:
    def __init__(
        self,
        result: ResearchResult,
    ) -> None:
        self.result = result
        self.requests = []

    async def research(
        self,
        request,
    ) -> ResearchResult:
        self.requests.append(request)
        return self.result


def _result() -> ResearchResult:
    return ResearchResult(
        answer="A verified answer.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="A supported claim.",
                evidence_ids=["evidence-1"],
                confidence=0.9,
            )
        ],
        claim_verifications=[
            ClaimVerification(
                claim_id="claim-1",
                verdict=ClaimSupport.SUPPORTED,
                confidence=0.98,
                supporting_evidence_ids=["evidence-1"],
                explanation=("The cited evidence directly supports it."),
            )
        ],
        usage=ResearchUsage(
            search_requests=1,
            pages_fetched=1,
            llm_calls=3,
            input_tokens=100,
            output_tokens=50,
            judgement_calls=2,
            judgement_input_tokens=500,
            judgement_output_tokens=0,
            judgement_cost_usd=0.000021,
            estimated_cost_usd=0.001021,
        ),
    )


def test_parser_accepts_repeatable_domains() -> None:
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
            "--domain",
            "python.org",
            "--domain",
            "docs.python.org",
        ]
    )

    assert args.allowed_domains == [
        "python.org",
        "docs.python.org",
    ]


def test_parser_uses_generic_research_budget_defaults() -> None:
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
        ]
    )

    assert args.max_searches == 10
    assert args.max_fetch_attempts == 40
    assert args.max_pages == 20
    assert args.max_bytes_per_page == 5_000_000
    assert args.max_total_bytes == 50_000_000
    assert args.max_llm_calls == 10
    assert args.max_input_tokens == 500_000
    assert args.max_output_tokens == 50_000


def test_parser_defaults_semantic_content_judgement_to_observe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT",
        raising=False,
    )
    monkeypatch.delenv(
        "OPENROUTER_JEV_MODEL",
        raising=False,
    )
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
        ]
    )

    assert args.content_judgement is ContentJudgementMode.OBSERVE
    assert args.jev_model == "typesafe/jev-1.13"


def test_parser_accepts_off_mode_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT",
        "off",
    )
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
        ]
    )

    assert args.content_judgement is ContentJudgementMode.OFF


def test_parser_flag_can_opt_out_of_environment_observe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT",
        "observe",
    )
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
            "--content-judgement",
            "off",
        ]
    )

    assert args.content_judgement is ContentJudgementMode.OFF


def test_service_builder_defaults_to_observe_mode() -> None:
    service = cli._build_service(
        brave_api_key="brave-test",
        openrouter_api_key="openrouter-test",
        model="test/model",
        verify=False,
    )

    observer = service._gatherer._content_judgement
    assert observer._policy.mode is ContentJudgementMode.OBSERVE
    assert observer._judge is not None


def test_service_builder_explicit_off_disables_judge() -> None:
    service = cli._build_service(
        brave_api_key="brave-test",
        openrouter_api_key="openrouter-test",
        model="test/model",
        verify=False,
        content_judgement_mode=ContentJudgementMode.OFF,
    )

    observer = service._gatherer._content_judgement
    assert observer._policy.mode is ContentJudgementMode.OFF
    assert observer._judge is None


def test_parser_accepts_observe_mode_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT",
        "observe",
    )
    monkeypatch.setenv(
        "OPENROUTER_JEV_MODEL",
        "typesafe/jev-1.13",
    )
    args = cli.build_parser().parse_args(
        [
            "research",
            "question",
        ]
    )

    assert args.content_judgement is ContentJudgementMode.OBSERVE
    assert args.jev_model == "typesafe/jev-1.13"


def test_human_renderer_surfaces_verification_and_usage() -> None:
    rendered = cli._render_human(_result())

    assert "A verified answer." in rendered
    assert "[supported (0.98)]" in rendered
    assert "evidence-1" in rendered
    assert "LLM calls: 3" in rendered
    assert "content judgement calls: 2" in rendered
    assert "content judgement cost USD: 0.000021" in rendered


def test_cli_json_output_runs_bounded_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(
        "BRAVE_API_KEY",
        "brave-test",
    )
    monkeypatch.setenv(
        "OPENROUTER_API_KEY",
        "openrouter-test",
    )

    service = _FakeService(_result())

    monkeypatch.setattr(
        cli,
        "_build_service",
        lambda **_: service,
    )

    exit_code = cli.main(
        [
            "research",
            "What changed?",
            "--domain",
            "python.org",
            "--json",
        ]
    )

    assert exit_code == 0
    assert len(service.requests) == 1
    assert service.requests[0].allowed_domains == ["python.org"]

    payload = json.loads(capsys.readouterr().out)

    assert payload["answer"] == "A verified answer."
    assert payload["claim_verifications"][0]["verdict"] == "supported"


def test_cli_reports_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(
        "BRAVE_API_KEY",
        raising=False,
    )
    monkeypatch.delenv(
        "OPENROUTER_API_KEY",
        raising=False,
    )

    exit_code = cli.main(
        [
            "research",
            "question",
        ]
    )

    assert exit_code == 2

    stderr = capsys.readouterr().err

    assert "BRAVE_API_KEY" in stderr
    assert "OPENROUTER_API_KEY" in stderr
