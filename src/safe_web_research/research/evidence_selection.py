import re
from collections.abc import Iterable
from dataclasses import dataclass

from safe_web_research.domain import EvidenceChunk, Source

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9._+-]*", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }
)


@dataclass(frozen=True, slots=True)
class EvidenceSelectionPolicy:
    """Soft evidence targets used for relevance selection and early stopping."""

    max_selected_chars: int = 200_000
    max_chunks_per_source: int = 8
    min_sources_for_sufficiency: int = 3
    min_relevant_chunks_for_sufficiency: int = 6
    target_selected_chars: int = 60_000
    min_question_term_coverage: float = 0.5

    def __post_init__(self) -> None:
        if self.max_selected_chars <= 0:
            raise ValueError("max_selected_chars must be greater than zero")
        if self.max_chunks_per_source <= 0:
            raise ValueError("max_chunks_per_source must be greater than zero")
        if self.min_sources_for_sufficiency <= 0:
            raise ValueError("min_sources_for_sufficiency must be greater than zero")
        if self.min_relevant_chunks_for_sufficiency <= 0:
            raise ValueError("min_relevant_chunks_for_sufficiency must be greater than zero")
        if self.target_selected_chars <= 0:
            raise ValueError("target_selected_chars must be greater than zero")
        if self.target_selected_chars > self.max_selected_chars:
            raise ValueError("target_selected_chars must not exceed max_selected_chars")
        if not 0.0 <= self.min_question_term_coverage <= 1.0:
            raise ValueError("min_question_term_coverage must be between zero and one")


@dataclass(frozen=True, slots=True)
class EvidenceSelection:
    """Deterministically selected evidence and sufficiency diagnostics."""

    sources: tuple[Source, ...]
    evidence: tuple[EvidenceChunk, ...]
    selected_chars: int
    relevant_chunks: int
    question_term_coverage: float
    sufficient: bool


@dataclass(frozen=True, slots=True)
class _Candidate:
    chunk: EvidenceChunk
    score: int
    matched_question_terms: frozenset[str]
    relevant: bool
    source_order: int


class EvidenceSelector:
    """Select compact, relevant, source-diverse evidence without another LLM call."""

    def __init__(
        self,
        policy: EvidenceSelectionPolicy | None = None,
    ) -> None:
        self._policy = policy or EvidenceSelectionPolicy()

    def select(
        self,
        *,
        question: str,
        queries: Iterable[str],
        sources: Iterable[Source],
        evidence: Iterable[EvidenceChunk],
    ) -> EvidenceSelection:
        source_list = list(sources)
        evidence_list = list(evidence)

        if not source_list or not evidence_list:
            return EvidenceSelection(
                sources=(),
                evidence=(),
                selected_chars=0,
                relevant_chunks=0,
                question_term_coverage=0.0,
                sufficient=False,
            )

        source_by_id = {source.source_id: source for source in source_list}
        source_order = {source.source_id: index for index, source in enumerate(source_list)}

        question_terms = self._terms(question)
        query_terms = set(question_terms)
        for query in queries:
            query_terms.update(self._terms(query))

        candidates: list[_Candidate] = []
        for chunk in evidence_list:
            source = source_by_id.get(chunk.source_id)
            if source is None:
                continue

            text_terms = self._terms(chunk.text)
            title_terms = self._terms(source.title)
            question_matches = question_terms & (text_terms | title_terms)
            query_matches = query_terms & (text_terms | title_terms)
            title_matches = query_terms & title_terms

            score = (
                10 * len(question_matches)
                + 4 * len(query_matches)
                + 3 * len(title_matches)
                + max(0, 3 - chunk.position)
            )

            candidates.append(
                _Candidate(
                    chunk=chunk,
                    score=score,
                    matched_question_terms=frozenset(question_matches),
                    relevant=bool(query_matches),
                    source_order=source_order[chunk.source_id],
                )
            )

        by_source: dict[str, list[_Candidate]] = {}
        for candidate in candidates:
            by_source.setdefault(candidate.chunk.source_id, []).append(candidate)

        for source_candidates in by_source.values():
            source_candidates.sort(key=lambda item: (-item.score, item.chunk.position))

        selected: list[_Candidate] = []
        selected_ids: set[str] = set()
        per_source_count: dict[str, int] = {}
        selected_chars = 0

        def try_add(candidate: _Candidate) -> bool:
            nonlocal selected_chars

            chunk = candidate.chunk
            if chunk.chunk_id in selected_ids:
                return False
            if per_source_count.get(chunk.source_id, 0) >= self._policy.max_chunks_per_source:
                return False

            additional_chars = len(chunk.text)
            if selected and selected_chars + additional_chars > self._policy.max_selected_chars:
                return False
            if not selected and additional_chars > self._policy.max_selected_chars:
                return False

            selected.append(candidate)
            selected_ids.add(chunk.chunk_id)
            per_source_count[chunk.source_id] = per_source_count.get(chunk.source_id, 0) + 1
            selected_chars += additional_chars
            return True

        # First pass guarantees source diversity before adding more chunks from strong sources.
        for source in source_list:
            source_candidates = by_source.get(source.source_id, [])
            if source_candidates:
                try_add(source_candidates[0])

        remaining = sorted(
            candidates,
            key=lambda item: (
                -item.score,
                item.source_order,
                item.chunk.position,
            ),
        )
        for candidate in remaining:
            try_add(candidate)

        selected.sort(key=lambda item: (item.source_order, item.chunk.position))

        matched_question_terms: set[str] = set()
        relevant_chunks = 0
        selected_source_ids: set[str] = set()

        for candidate in selected:
            matched_question_terms.update(candidate.matched_question_terms)
            if candidate.relevant:
                relevant_chunks += 1
            selected_source_ids.add(candidate.chunk.source_id)

        if question_terms:
            question_term_coverage = len(matched_question_terms) / len(question_terms)
        else:
            question_term_coverage = 1.0

        selected_sources = tuple(
            source for source in source_list if source.source_id in selected_source_ids
        )
        selected_evidence = tuple(candidate.chunk for candidate in selected)

        sufficient = (
            len(selected_sources) >= self._policy.min_sources_for_sufficiency
            and relevant_chunks >= self._policy.min_relevant_chunks_for_sufficiency
            and selected_chars >= self._policy.target_selected_chars
            and question_term_coverage >= self._policy.min_question_term_coverage
        )

        return EvidenceSelection(
            sources=selected_sources,
            evidence=selected_evidence,
            selected_chars=selected_chars,
            relevant_chunks=relevant_chunks,
            question_term_coverage=question_term_coverage,
            sufficient=sufficient,
        )

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            match.group(0).casefold()
            for match in _WORD_RE.finditer(text)
            if len(match.group(0)) >= 2 and match.group(0).casefold() not in _STOP_WORDS
        }
