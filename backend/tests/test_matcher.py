from app.services.matcher import match_numbers, MatchProposal


def test_simple_one_to_one():
    """3 audio numbers, 3 OCR with same values → all matched."""
    audio = [23.0, 5.0, 12.0]
    ocr = [(101, 23.0), (102, 5.0), (103, 12.0)]
    proposals = match_numbers(audio, ocr)

    assert len(proposals) == 3
    matched = {p.audio_index: p.ocr_id for p in proposals if p.ocr_id is not None}
    assert matched == {0: 101, 1: 102, 2: 103}
    assert all(p.confidence == 1.0 for p in proposals if p.ocr_id is not None)


def test_audio_with_extra_ocr_numbers():
    """5 OCR but audio only has 3 → 2 OCR ignored."""
    audio = [23.0, 5.0, 12.0]
    ocr = [(101, 23.0), (102, 5.0), (103, 12.0), (104, 99.0), (105, 7.0)]
    proposals = match_numbers(audio, ocr)
    matched_ocr = {p.ocr_id for p in proposals if p.ocr_id is not None}
    assert matched_ocr == {101, 102, 103}


def test_audio_value_with_no_ocr_match():
    """Audio has 99 but no OCR has 99 → unmatched."""
    audio = [23.0, 99.0, 12.0]
    ocr = [(101, 23.0), (102, 5.0), (103, 12.0)]
    proposals = match_numbers(audio, ocr)
    by_index = {p.audio_index: p for p in proposals}
    assert by_index[0].ocr_id == 101
    assert by_index[1].ocr_id is None  # 99 unmatched
    assert by_index[2].ocr_id == 103


def test_repeated_audio_value_matches_same_ocr_twice():
    """Rule '2a': audio reads 23 twice → same OCR matched twice."""
    audio = [23.0, 23.0, 12.0]
    ocr = [(101, 23.0), (102, 12.0)]
    proposals = match_numbers(audio, ocr)
    matched = [p.ocr_id for p in proposals]
    assert matched == [101, 101, 102]


def test_duplicate_ocr_values_uses_least_used_first():
    """Two OCR with value 23, audio reads 23 twice → both ocr used (one each), not same one twice."""
    audio = [23.0, 23.0]
    ocr = [(101, 23.0), (102, 23.0)]
    proposals = match_numbers(audio, ocr)
    matched = [p.ocr_id for p in proposals]
    # Must use both OCR (lower assigned_count preferred)
    assert sorted(matched) == [101, 102]


def test_existing_matches_influence_assignment():
    """If 101 already has 2 matches, prefer 102 for the same value."""
    audio = [23.0]
    ocr = [(101, 23.0), (102, 23.0)]
    existing_counts = {101: 2, 102: 0}
    proposals = match_numbers(audio, ocr, existing_match_counts=existing_counts)
    assert proposals[0].ocr_id == 102  # less used


def test_empty_audio_returns_empty():
    assert match_numbers([], [(101, 23.0)]) == []


def test_empty_ocr_all_unmatched():
    audio = [23.0, 5.0]
    proposals = match_numbers(audio, [])
    assert all(p.ocr_id is None for p in proposals)
    assert [p.audio_index for p in proposals] == [0, 1]


def test_proposals_preserve_audio_order():
    """Output proposals must be in audio_index order 0,1,2,..."""
    audio = [12.0, 23.0, 5.0]
    ocr = [(101, 23.0), (102, 12.0), (103, 5.0)]
    proposals = match_numbers(audio, ocr)
    assert [p.audio_index for p in proposals] == [0, 1, 2]


def test_match_proposal_is_dataclass():
    p = MatchProposal(audio_index=0, ocr_id=101, confidence=1.0)
    assert p.audio_index == 0
    assert p.ocr_id == 101
    assert p.confidence == 1.0
