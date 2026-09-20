import pytest
from pydantic import ValidationError

from safe_web_research.domain import FetchRequest


def test_fetch_request_has_safe_defaults() -> None:
    request = FetchRequest(url="https://example.com/")

    assert request.max_bytes == 2_000_000
    assert request.max_redirects == 5


def test_fetch_request_rejects_negative_size_limit() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com/",
            max_bytes=-1,
        )


def test_fetch_request_rejects_excessive_redirect_limit() -> None:
    with pytest.raises(ValidationError):
        FetchRequest(
            url="https://example.com/",
            max_redirects=21,
        )
