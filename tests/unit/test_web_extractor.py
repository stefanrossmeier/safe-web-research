import pytest

from safe_web_research.domain import FetchedDocument
from safe_web_research.extraction import (
    EmptyContentError,
    UnsupportedContentTypeError,
    WebExtractor,
)


@pytest.mark.asyncio
async def test_html_extraction_prefers_main_content() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/article",
        final_url="https://example.com/article",
        status_code=200,
        content_type="text/html",
        body=b"""
        <html>
          <head>
            <title> Example Article </title>
            <script>secret_script()</script>
          </head>
          <body>
            <nav>Navigation noise</nav>
            <main>
              <h1>Main heading</h1>
              <p>Useful factual content.</p>
            </main>
            <footer>Footer noise</footer>
          </body>
        </html>
        """,
    )

    extractor = WebExtractor()

    result = await extractor.extract(document)

    assert result.source.title == "Example Article"
    assert result.source.provider == "web"

    text = "\n".join(chunk.text for chunk in result.chunks)

    assert "Main heading" in text
    assert "Useful factual content." in text
    assert "Navigation noise" not in text
    assert "Footer noise" not in text
    assert "secret_script" not in text


@pytest.mark.asyncio
async def test_plain_text_extraction_normalizes_whitespace() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/data.txt",
        final_url="https://example.com/data.txt",
        status_code=200,
        content_type="text/plain",
        body=b"first   line\n\n second    line ",
    )

    result = await WebExtractor().extract(document)

    assert [chunk.text for chunk in result.chunks] == ["first line\n\nsecond line"]


@pytest.mark.asyncio
async def test_extraction_is_deterministic() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/plain",
        body=b"deterministic text",
    )

    extractor = WebExtractor()

    first = await extractor.extract(document)

    second = await extractor.extract(document)

    assert first.source.source_id == second.source.source_id

    assert first.source.content_hash == second.source.content_hash

    assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]


@pytest.mark.asyncio
async def test_extractor_chunks_long_content() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/plain",
        body=(b"one two three four five six seven eight nine ten eleven twelve"),
    )

    result = await WebExtractor(max_chunk_chars=20).extract(document)

    assert len(result.chunks) > 1

    assert all(len(chunk.text) <= 20 for chunk in result.chunks)


@pytest.mark.asyncio
async def test_extractor_rejects_unsupported_content_type() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/file.pdf",
        final_url="https://example.com/file.pdf",
        status_code=200,
        content_type="application/pdf",
        body=b"%PDF",
    )

    with pytest.raises(UnsupportedContentTypeError):
        await WebExtractor().extract(document)


@pytest.mark.asyncio
async def test_extractor_rejects_empty_document() -> None:
    document = FetchedDocument(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/html",
        body=b"<html><script>ignored()</script></html>",
    )

    with pytest.raises(EmptyContentError):
        await WebExtractor().extract(document)
