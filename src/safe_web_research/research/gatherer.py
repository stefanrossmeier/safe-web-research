from collections.abc import Sequence

from safe_web_research.domain import (
    EvidenceBundle,
    FetchRequest,
    ResearchRequest,
    SearchRequest,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)
from safe_web_research.extraction import (
    ExtractionError,
    Extractor,
)
from safe_web_research.fetch import (
    Fetcher,
    FetchError,
    FetchPolicyError,
)
from safe_web_research.research.budget import BudgetTracker
from safe_web_research.research.stopping import StoppingPolicy
from safe_web_research.search import (
    SearchProvider,
    SearchProviderError,
)
from safe_web_research.security import SuspiciousContentScanner


class EvidenceGatherer:
    """Turn research queries into bounded, provenance-preserving evidence."""

    def __init__(
        self,
        search_provider: SearchProvider,
        fetcher: Fetcher,
        extractor: Extractor,
        *,
        stopping_policy: StoppingPolicy | None = None,
        content_scanner: SuspiciousContentScanner | None = None,
    ) -> None:
        self._search_provider = search_provider
        self._fetcher = fetcher
        self._extractor = extractor
        self._stopping_policy = stopping_policy or StoppingPolicy()
        self._content_scanner = content_scanner or SuspiciousContentScanner()

    async def gather(
        self,
        request: ResearchRequest,
        *,
        queries: Sequence[str] | None = None,
    ) -> EvidenceBundle:
        candidate_queries = self._normalize_queries(
            queries if queries is not None else [request.question]
        )

        tracker = BudgetTracker(request.budget)

        issued_queries: list[str] = []
        sources = []
        evidence = []
        security_events: list[SecurityEvent] = []
        incomplete_reasons: list[str] = []

        seen_urls: set[str] = set()
        seen_content_hashes: set[str] = set()

        consecutive_empty_queries = 0

        for query in candidate_queries:
            if tracker.fetch_exhausted:
                self._add_fetch_budget_reason(
                    tracker,
                    incomplete_reasons,
                )
                break

            if not tracker.reserve_search():
                self._add_reason(
                    incomplete_reasons,
                    "max_searches_reached",
                )
                break

            issued_queries.append(query)

            max_results = max(
                1,
                min(
                    20,
                    tracker.remaining_fetch_attempts,
                ),
            )

            try:
                results = await self._search_provider.search(
                    SearchRequest(
                        query=query,
                        max_results=max_results,
                        freshness_days=request.freshness_days,
                        include_domains=request.allowed_domains,
                        exclude_domains=request.blocked_domains,
                        language=request.language,
                        country=request.country,
                    )
                )

            except SearchProviderError as exc:
                security_events.append(
                    SecurityEvent(
                        event_type=SecurityEventType.PROVIDER_ERROR,
                        severity=SecuritySeverity.WARNING,
                        message=str(exc),
                        source="search",
                        metadata={
                            "query": query,
                        },
                    )
                )

                consecutive_empty_queries += 1

                if self._stopping_policy.should_stop(consecutive_empty_queries):
                    self._add_reason(
                        incomplete_reasons,
                        "no_new_evidence",
                    )
                    break

                continue

            new_evidence = 0
            stop_for_budget = False

            for result in results:
                url_key = str(result.url)

                if url_key in seen_urls:
                    continue

                seen_urls.add(url_key)

                max_bytes = tracker.reserve_fetch()

                if max_bytes is None:
                    self._add_fetch_budget_reason(
                        tracker,
                        incomplete_reasons,
                    )
                    stop_for_budget = True
                    break

                try:
                    document = await self._fetcher.fetch(
                        FetchRequest(
                            url=result.url,
                            max_bytes=max_bytes,
                            max_redirects=request.budget.max_redirects,
                        )
                    )

                except FetchPolicyError as exc:
                    security_events.append(
                        SecurityEvent(
                            event_type=SecurityEventType.POLICY_VIOLATION,
                            severity=SecuritySeverity.HIGH,
                            message=str(exc),
                            source=url_key,
                        )
                    )
                    continue

                except FetchError as exc:
                    security_events.append(
                        SecurityEvent(
                            event_type=SecurityEventType.FETCH_ERROR,
                            severity=SecuritySeverity.WARNING,
                            message=str(exc),
                            source=url_key,
                        )
                    )
                    continue

                tracker.record_fetch_success(len(document.body))

                try:
                    extracted = await self._extractor.extract(document)

                except ExtractionError as exc:
                    security_events.append(
                        SecurityEvent(
                            event_type=SecurityEventType.EXTRACTION_ERROR,
                            severity=SecuritySeverity.WARNING,
                            message=str(exc),
                            source=url_key,
                        )
                    )
                    continue

                for chunk in extracted.chunks:
                    for finding in self._content_scanner.scan(chunk.text):
                        security_events.append(
                            SecurityEvent(
                                event_type=SecurityEventType.SUSPICIOUS_CONTENT,
                                severity=SecuritySeverity.WARNING,
                                message=finding.description,
                                source=url_key,
                                metadata={
                                    "rule_id": finding.rule_id,
                                    "evidence_id": chunk.chunk_id,
                                },
                            )
                        )

                content_hash = extracted.source.content_hash

                if content_hash in seen_content_hashes:
                    continue

                seen_content_hashes.add(content_hash)

                sources.append(extracted.source)

                evidence.extend(extracted.chunks)

                new_evidence += len(extracted.chunks)

            if stop_for_budget:
                break

            if new_evidence == 0:
                consecutive_empty_queries += 1
            else:
                consecutive_empty_queries = 0

            if self._stopping_policy.should_stop(consecutive_empty_queries):
                self._add_reason(
                    incomplete_reasons,
                    "no_new_evidence",
                )
                break

        return EvidenceBundle(
            queries=issued_queries,
            sources=sources,
            evidence=evidence,
            security_events=security_events,
            usage=tracker.usage(),
            incomplete_reasons=incomplete_reasons,
        )

    @staticmethod
    def _normalize_queries(
        queries: Sequence[str],
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for query in queries:
            cleaned = " ".join(query.split())

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(cleaned)

        return normalized

    @staticmethod
    def _add_reason(
        reasons: list[str],
        reason: str,
    ) -> None:
        if reason not in reasons:
            reasons.append(reason)

    @classmethod
    def _add_fetch_budget_reason(
        cls,
        tracker: BudgetTracker,
        reasons: list[str],
    ) -> None:
        if tracker.remaining_fetch_attempts == 0:
            cls._add_reason(
                reasons,
                "max_pages_reached",
            )

        if tracker.remaining_bytes == 0:
            cls._add_reason(
                reasons,
                "max_total_bytes_reached",
            )
