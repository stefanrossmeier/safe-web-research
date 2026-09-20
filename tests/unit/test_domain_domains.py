import pytest
from pydantic import ValidationError

from safe_web_research.domain import ResearchRequest, SearchRequest


def test_search_request_normalizes_domains() -> None:
    request = SearchRequest(
        query="python",
        include_domains=["Docs.Python.org"],
        exclude_domains=["Example.COM"],
    )

    assert request.include_domains == ["docs.python.org"]
    assert request.exclude_domains == ["example.com"]


@pytest.mark.parametrize(
    "domain",
    [
        "https://example.com",
        "example.com/path",
        "example.com:443",
        "*.example.com",
        "example.com OR site:evil.example",
        "example com",
    ],
)
def test_search_request_rejects_non_domain_input(
    domain: str,
) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="test",
            include_domains=[domain],
        )


def test_research_request_rejects_search_operator_as_domain() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            question="test",
            allowed_domains=["example.com OR site:evil.example"],
        )
