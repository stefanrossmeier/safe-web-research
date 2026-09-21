from pathlib import Path

from benchmarks.content_judgement.models import EvaluationSuite
from safe_web_research.security import SuspiciousContentScanner

_CASES = Path(__file__).resolve().parents[2] / "benchmarks" / "content_judgement" / "cases.json"


def test_content_judgement_corpus_has_20_hard_negatives_and_20_attacks() -> None:
    suite = EvaluationSuite.from_path(_CASES)

    benign = [case for case in suite.cases if case.expected == "benign"]
    malicious = [case for case in suite.cases if case.expected == "malicious"]

    assert len(suite.cases) == 40
    assert len(benign) == 20
    assert len(malicious) == 20
    assert len({case.case_id for case in suite.cases}) == 40
    assert {case.family for case in benign} == {case.family for case in malicious}


def test_benign_cases_are_intentionally_security_relevant() -> None:
    suite = EvaluationSuite.from_path(_CASES)
    benign_text = "\n".join(
        case.content.lower() for case in suite.cases if case.expected == "benign"
    )

    for marker in (
        "ignore",
        "system prompt",
        "shell",
        "api key",
        "127.0.0.1",
        "tool",
        "citation",
        "developer",
    ):
        assert marker in benign_text


def test_benign_half_contains_many_regex_hard_negatives() -> None:
    suite = EvaluationSuite.from_path(_CASES)
    scanner = SuspiciousContentScanner()
    benign = [case for case in suite.cases if case.expected == "benign"]
    malicious = [case for case in suite.cases if case.expected == "malicious"]

    benign_flagged = sum(bool(scanner.scan(case.content)) for case in benign)
    malicious_flagged = sum(bool(scanner.scan(case.content)) for case in malicious)

    assert benign_flagged >= 12
    assert malicious_flagged < len(malicious)
