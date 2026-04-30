"""Pure match engine: pairs audio-spoken numbers with OCR-detected numbers.

Phase-1 strategy: exact value equality only. Same OCR can be matched multiple
times within a single group (rule "2a + 2c"). When multiple OCR rows have the
same value, the one with the lowest existing match count is preferred (avoids
piling all matches on the first row).

This module is pure: no DB, no I/O. The API layer persists `Match` rows from
the proposals returned here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MatchProposal:
    """One proposed match per audio number (in audio order). ocr_id=None = unmatched."""
    audio_index: int
    ocr_id: int | None
    confidence: float  # 1.0 for exact match, 0 for unmatched


def match_numbers(
    audio_numbers: list[float],
    ocr_pairs: Iterable[tuple[int, float]],
    existing_match_counts: dict[int, int] | None = None,
) -> list[MatchProposal]:
    """Greedy exact-value matcher.

    Args:
        audio_numbers: numbers parsed from audio, in spoken order.
        ocr_pairs: list of (ocr_id, effective_value).
        existing_match_counts: per-ocr_id count of matches already created
            in OTHER groups (used to break ties when picking among duplicates).

    Returns:
        One MatchProposal per audio number (same order). ocr_id=None means
        no exact match was found.
    """
    existing_match_counts = existing_match_counts or {}

    # Group OCR rows by value for O(1) lookup
    ocr_by_value: dict[float, list[int]] = {}
    for ocr_id, val in ocr_pairs:
        ocr_by_value.setdefault(val, []).append(ocr_id)

    # In-call usage counter (matches we've proposed in THIS call)
    in_call_use: dict[int, int] = {}

    proposals: list[MatchProposal] = []
    for idx, target in enumerate(audio_numbers):
        candidates = ocr_by_value.get(target)
        if not candidates:
            proposals.append(MatchProposal(audio_index=idx, ocr_id=None, confidence=0.0))
            continue

        # Pick candidate with lowest combined (existing + in-call) count
        def _score(oid: int) -> tuple[int, int]:
            return (existing_match_counts.get(oid, 0) + in_call_use.get(oid, 0), oid)

        best = min(candidates, key=_score)
        in_call_use[best] = in_call_use.get(best, 0) + 1
        proposals.append(MatchProposal(audio_index=idx, ocr_id=best, confidence=1.0))

    return proposals
