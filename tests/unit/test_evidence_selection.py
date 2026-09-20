from datetime import UTC, datetime

from safe_web_research.domain import EvidenceChunk, Source
from safe_web_research.research import (
    EvidenceSelectionPolicy,
    EvidenceSelector,
)


def _source(index: int) -> Source:
    return Source(
        source_id=f"source-{index}",
        url=f"https://example{index}.com/",
        title=f"Python UTF-8 source {index}",
        provider="fake",
        retrieved_at=datetime(2026, 9, 20, tzinfo=UTC),
        content_hash=f"{index}" * 64,
    )


def _chunk(source_index: int, position: int, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=f"evidence-{source_index}-{position}",
        source_id=f"source-{source_index}",
        text=text,
        position=position,
    )


def test_selector_prefers_relevant_source_diverse_evidence() -> None:
    sources = [_source(1), _source(2), _source(3)]
    evidence = [
        _chunk(1, 0, "Python 3.15 changes the default encoding to UTF-8."),
        _chunk(1, 1, "Unrelated implementation detail."),
        _chunk(2, 0, "UTF-8 is the default encoding in Python 3.15."),
        _chunk(2, 1, "Another unrelated paragraph."),
        _chunk(3, 0, "Python documentation explains the UTF-8 default."),
    ]

    selector = EvidenceSelector(
        EvidenceSelectionPolicy(
            max_selected_chars=500,
            max_chunks_per_source=1,
            min_sources_for_sufficiency=3,
            min_relevant_chunks_for_sufficiency=3,
            target_selected_chars=80,
            min_question_term_coverage=0.5,
        )
    )

    selection = selector.select(
        question="What changed about Python 3.15 default encoding?",
        queries=["Python 3.15 UTF-8 default encoding"],
        sources=sources,
        evidence=evidence,
    )

    assert [source.source_id for source in selection.sources] == [
        "source-1",
        "source-2",
        "source-3",
    ]
    assert [chunk.position for chunk in selection.evidence] == [0, 0, 0]
    assert selection.relevant_chunks == 3
    assert selection.question_term_coverage >= 0.5
    assert selection.sufficient


def test_selector_keeps_gathering_when_evidence_is_not_relevant_enough() -> None:
    sources = [
        _source(1).model_copy(update={"title": "Unrelated source one"}),
        _source(2).model_copy(update={"title": "Unrelated source two"}),
        _source(3).model_copy(update={"title": "Unrelated source three"}),
    ]
    evidence = [
        _chunk(1, 0, "Completely unrelated material."),
        _chunk(2, 0, "More unrelated material."),
        _chunk(3, 0, "Still unrelated material."),
    ]

    selector = EvidenceSelector(
        EvidenceSelectionPolicy(
            max_selected_chars=500,
            max_chunks_per_source=1,
            min_sources_for_sufficiency=3,
            min_relevant_chunks_for_sufficiency=2,
            target_selected_chars=20,
            min_question_term_coverage=0.5,
        )
    )

    selection = selector.select(
        question="How does Python configure TLS certificates?",
        queries=["Python TLS certificate configuration"],
        sources=sources,
        evidence=evidence,
    )

    assert not selection.sufficient
    assert selection.relevant_chunks == 0
    assert selection.question_term_coverage < 0.5


def test_default_policy_stops_with_compact_relevant_two_source_evidence() -> None:
    sources = [_source(1), _source(2)]
    paragraph = (
        "Python 3.15 changes the default encoding to UTF-8 and documents how "
        "the previous behavior can be restored. "
    )
    evidence = [
        _chunk(source_index, position, paragraph * 40)
        for source_index in (1, 2)
        for position in (0, 1)
    ]

    selection = EvidenceSelector().select(
        question="What changed about Python 3.15 default encoding?",
        queries=["Python 3.15 UTF-8 default encoding"],
        sources=sources,
        evidence=evidence,
    )

    assert len(selection.sources) == 2
    assert selection.relevant_chunks == 4
    assert selection.selected_chars >= 16_000
    assert selection.question_term_coverage >= 0.5
    assert selection.sufficient
