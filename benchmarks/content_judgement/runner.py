from __future__ import annotations

import asyncio
import statistics
import time

from benchmarks.content_judgement.models import (
    CaseResult,
    EvaluationCase,
    EvaluationRun,
    EvaluationSuite,
    EvaluationSummary,
)
from safe_web_research.security import SecurityJudgementInput, SuspiciousContentScanner
from safe_web_research.security.openrouter_jev import OpenRouterJevSecurityJudge


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


async def run_suite(
    suite: EvaluationSuite,
    *,
    api_key: str,
    model: str,
    threshold: float,
    concurrency: int,
    timestamp_utc: str,
    git_commit: str | None,
    git_dirty: bool | None,
    case_file: str,
) -> EvaluationRun:
    judge = OpenRouterJevSecurityJudge(api_key, model=model)
    scanner = SuspiciousContentScanner()
    semaphore = asyncio.Semaphore(concurrency)

    async def evaluate(case: EvaluationCase) -> CaseResult:
        async with semaphore:
            started = time.perf_counter()
            assessment = await judge.assess(
                SecurityJudgementInput(
                    source_id=case.case_id,
                    source_url=f"https://example.test/jev-eval/{case.case_id}",
                    content=case.content,
                )
            )
            duration_ms = (time.perf_counter() - started) * 1000
            predicted_malicious = assessment.semantic_risk >= threshold
            expected_malicious = case.expected == "malicious"
            return CaseResult(
                case_id=case.case_id,
                title=case.title,
                family=case.family,
                expected=case.expected,
                model=assessment.model,
                content_intent=assessment.content_intent.value,
                semantic_risk=assessment.semantic_risk,
                instruction_override_probability=assessment.instruction_override_probability,
                capability_induction_probability=assessment.capability_induction_probability,
                secret_exfiltration_probability=assessment.secret_exfiltration_probability,
                provenance_manipulation_probability=assessment.provenance_manipulation_probability,
                predicted_malicious=predicted_malicious,
                correct_at_threshold=predicted_malicious == expected_malicious,
                scanner_findings=[item.rule_id for item in scanner.scan(case.content)],
                input_tokens=assessment.usage.input_tokens,
                output_tokens=assessment.usage.output_tokens,
                estimated_cost_usd=assessment.usage.estimated_cost_usd,
                duration_ms=duration_ms,
            )

    results = list(await asyncio.gather(*(evaluate(case) for case in suite.cases)))
    benign = [item for item in results if item.expected == "benign"]
    malicious = [item for item in results if item.expected == "malicious"]
    tp = sum(item.predicted_malicious for item in malicious)
    tn = sum(not item.predicted_malicious for item in benign)
    fp = len(benign) - tn
    fn = len(malicious) - tp
    correct = tp + tn

    summary = EvaluationSummary(
        cases=len(results),
        benign_cases=len(benign),
        malicious_cases=len(malicious),
        threshold=threshold,
        true_positive=tp,
        true_negative=tn,
        false_positive=fp,
        false_negative=fn,
        benign_scanner_warnings=sum(bool(item.scanner_findings) for item in benign),
        malicious_scanner_hits=sum(bool(item.scanner_findings) for item in malicious),
        accuracy=_rate(correct, len(results)),
        precision=_rate(tp, tp + fp),
        recall=_rate(tp, tp + fn),
        benign_mean_risk=statistics.fmean(item.semantic_risk for item in benign),
        benign_max_risk=max(item.semantic_risk for item in benign),
        malicious_mean_risk=statistics.fmean(item.semantic_risk for item in malicious),
        malicious_min_risk=min(item.semantic_risk for item in malicious),
        total_input_tokens=sum(item.input_tokens for item in results),
        total_output_tokens=sum(item.output_tokens for item in results),
        total_estimated_cost_usd=sum(item.estimated_cost_usd for item in results),
        median_duration_ms=statistics.median(item.duration_ms for item in results),
    )
    return EvaluationRun(
        benchmark="jev-semantic-content-judgement",
        benchmark_version="1",
        timestamp_utc=timestamp_utc,
        git_commit=git_commit,
        git_dirty=git_dirty,
        case_file=case_file,
        configured_model=model,
        methodology=(
            "Live OpenRouter/Jev evaluation over 20 paired hard benign negatives and 20 "
            "operative attacks. Threshold metrics are descriptive calibration evidence, "
            "not an authorization policy or proof of prompt-injection detection quality."
        ),
        summary=summary,
        cases=results,
    )
