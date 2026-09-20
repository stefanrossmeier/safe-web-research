from hashlib import sha256

from bs4 import BeautifulSoup, Tag

from safe_web_research.domain.evidence import EvidenceChunk, Source
from safe_web_research.domain.extraction import ExtractedDocument
from safe_web_research.domain.fetch import FetchedDocument
from safe_web_research.extraction.base import Extractor
from safe_web_research.extraction.errors import (
    EmptyContentError,
    UnsupportedContentTypeError,
)

_SUPPORTED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
)

_REMOVED_HTML_ELEMENTS = (
    "script, style, noscript, template, svg, canvas, iframe, nav, footer, aside, form"
)


class WebExtractor(Extractor):
    """Extract deterministic text evidence from bounded web documents."""

    def __init__(
        self,
        *,
        max_chunk_chars: int = 4_000,
    ) -> None:
        if max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars must be greater than zero")

        self._max_chunk_chars = max_chunk_chars

    async def extract(
        self,
        document: FetchedDocument,
    ) -> ExtractedDocument:
        content_type = document.content_type.lower()

        if content_type not in _SUPPORTED_CONTENT_TYPES:
            raise UnsupportedContentTypeError(f"Unsupported content type: {content_type}")

        if content_type == "text/plain":
            title = self._fallback_title(document)
            text = self._extract_plain_text(document.body)
        else:
            title, text = self._extract_html(
                document.body,
                fallback_title=self._fallback_title(document),
            )

        if not text:
            raise EmptyContentError("Document contains no usable textual content")

        content_hash = sha256(text.encode("utf-8")).hexdigest()

        source_id = self._source_id(str(document.final_url))

        source = Source(
            source_id=source_id,
            url=document.final_url,
            title=title,
            provider="web",
            retrieved_at=document.retrieved_at,
            content_hash=content_hash,
        )

        chunks = [
            EvidenceChunk(
                chunk_id=self._chunk_id(
                    source_id,
                    position,
                    chunk,
                ),
                source_id=source_id,
                text=chunk,
                position=position,
            )
            for position, chunk in enumerate(self._chunk_text(text))
        ]

        return ExtractedDocument(
            source=source,
            chunks=chunks,
        )

    def _extract_html(
        self,
        body: bytes,
        *,
        fallback_title: str,
    ) -> tuple[str, str]:
        soup = BeautifulSoup(
            body,
            "html.parser",
        )

        title_tag = soup.find("title")

        if isinstance(title_tag, Tag):
            title = self._normalize_inline(
                title_tag.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            title = fallback_title

        if not title:
            title = fallback_title

        for element in soup.select(_REMOVED_HTML_ELEMENTS):
            element.decompose()

        container: Tag | BeautifulSoup = soup

        main = soup.find("main")

        if isinstance(main, Tag):
            container = main
        else:
            article = soup.find("article")

            if isinstance(article, Tag):
                container = article
            elif isinstance(soup.body, Tag):
                container = soup.body

        text = self._normalize_multiline(
            container.get_text(
                "\n",
                strip=True,
            )
        )

        return title, text

    @classmethod
    def _extract_plain_text(
        cls,
        body: bytes,
    ) -> str:
        return cls._normalize_multiline(
            body.decode(
                "utf-8",
                errors="replace",
            )
        )

    def _chunk_text(
        self,
        text: str,
    ) -> list[str]:
        paragraphs = [paragraph for paragraph in text.split("\n\n") if paragraph]

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            for piece in self._split_long_paragraph(paragraph):
                candidate = piece if not current else f"{current}\n\n{piece}"

                if len(candidate) <= self._max_chunk_chars:
                    current = candidate
                    continue

                if current:
                    chunks.append(current)

                current = piece

        if current:
            chunks.append(current)

        return chunks

    def _split_long_paragraph(
        self,
        paragraph: str,
    ) -> list[str]:
        if len(paragraph) <= self._max_chunk_chars:
            return [paragraph]

        remaining = paragraph
        pieces: list[str] = []

        while len(remaining) > self._max_chunk_chars:
            split_at = remaining.rfind(
                " ",
                0,
                self._max_chunk_chars + 1,
            )

            if split_at <= 0:
                split_at = self._max_chunk_chars

            piece = remaining[:split_at].strip()

            if piece:
                pieces.append(piece)

            remaining = remaining[split_at:].strip()

        if remaining:
            pieces.append(remaining)

        return pieces

    @staticmethod
    def _normalize_inline(
        text: str,
    ) -> str:
        return " ".join(text.split())

    @classmethod
    def _normalize_multiline(
        cls,
        text: str,
    ) -> str:
        paragraphs = []

        for line in text.splitlines():
            normalized = cls._normalize_inline(line)

            if normalized:
                paragraphs.append(normalized)

        return "\n\n".join(paragraphs)

    @staticmethod
    def _fallback_title(
        document: FetchedDocument,
    ) -> str:
        return document.final_url.host or str(document.final_url)

    @staticmethod
    def _source_id(
        url: str,
    ) -> str:
        digest = sha256(url.encode("utf-8")).hexdigest()[:16]

        return f"source-{digest}"

    @staticmethod
    def _chunk_id(
        source_id: str,
        position: int,
        text: str,
    ) -> str:
        material = f"{source_id}:{position}:{text}"

        digest = sha256(material.encode("utf-8")).hexdigest()[:20]

        return f"evidence-{digest}"
