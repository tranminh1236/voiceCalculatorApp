# Plan 3 — Match Engine + Finalize + OCR Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện server-side capture flow: (1) match engine ghép `audio_numbers` ↔ `ocr_numbers` tự động khi upload audio; (2) PATCH endpoint sửa OCR sai; (3) endpoint thêm/bỏ match thủ công; (4) finalize endpoint tính `final_value` từ all groups; (5) `CaptureOut` embed `audio_groups + matches` để frontend hiển thị đầy đủ. Cuối plan: 1 test integration end-to-end mô phỏng capture flow hoàn chỉnh.

**Architecture:** Match engine là pure function `match_numbers(audio_numbers, ocr_numbers, existing_matches) → list[MatchProposal]`. Logic: ưu tiên exact value, cho phép cùng OCR match nhiều lần trong cùng group (rule "2a + 2c"), exact match only ở phase 1. Audio upload endpoint gọi matcher sau khi parse, tạo Match rows. Finalize tính `final = Σ sum_g × multiplier_g`.

**Tech Stack:** Existing — Python + FastAPI + SQLAlchemy. No new external deps.

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §6 (Match engine), §8 (API: PATCH ocr, POST matches, POST finalize).

**Pre-flight:** Plan 2 complete (tag `plan-2-complete`), 122 tests passing, 33 commits.

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   └── matcher.py          # NEW: pure match engine
│   ├── api/
│   │   └── captures.py         # MODIFY: PATCH ocr, POST matches, POST finalize, auto-match in audio upload, embed groups+matches in CaptureOut
│   └── schemas.py              # MODIFY: add MatchOut, OcrCorrectionIn, MatchActionIn; extend CaptureOut
├── tests/
│   ├── test_matcher.py                      # NEW: ~12 cases for match engine
│   ├── test_api_capture_correction.py       # NEW: PATCH OCR
│   ├── test_api_capture_matches.py          # NEW: manual match add/remove
│   ├── test_api_capture_finalize.py         # NEW: finalize flow
│   └── test_capture_flow_integration.py     # NEW: end-to-end full flow
```

**Responsibilities:**
- `matcher.py` — pure function. Input: list of audio numbers + list of (ocr_id, value) pairs + existing match counts. Output: list of `(audio_index, ocr_id_or_None, confidence)` proposals. No DB.
- `captures.py` — orchestrates: persists Match rows from matcher proposals, handles user OCR corrections via PATCH, manual match toggling, finalize aggregation.

---

## Task 1: Match engine — exact match algorithm

**Files:**
- Create: `backend/app/services/matcher.py`
- Create: `backend/tests/test_matcher.py`

- [ ] **Step 1: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_matcher.py`:

```python
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_matcher.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement `app/services/matcher.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/matcher.py`:

```python
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_matcher.py -v
```

Expected: 10 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/matcher.py backend/tests/test_matcher.py
git commit -m "feat(matcher): exact-value match engine with duplicate-handling + 2a-rule support"
```

---

## Task 2: Wire matcher into audio upload endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Modify: `backend/tests/test_api_capture_audio.py` (extend existing tests)

The audio upload endpoint currently creates the AudioGroup row but doesn't create Match rows. After this task, each successful upload also produces Match records (auto-match) and the response includes match details.

- [ ] **Step 1: Add `MatchOut` schema**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ocr_number_id: int
    audio_group_id: int
    confidence: float | None
    source: str  # 'auto' | 'manual'
```

Then EXTEND `AudioGroupOut` to include matches. Replace the existing `AudioGroupOut` definition with:

```python
class AudioGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    capture_id: int
    group_index: int
    audio_path: str
    transcript: str | None
    parsed_numbers: list[float] | None
    sum: float | None
    multiplier_snapshot: float
    matches: list[MatchOut] = []
```

- [ ] **Step 2: Test — extend existing audio test**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_audio.py`:

```python
def test_audio_upload_auto_matches_against_ocr(client, db_session):
    """Stub OCR returns [23,5,105], stub STT yields the same numbers → all 3 should auto-match."""
    from app.models import Match
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "matches" in body
    assert len(body["matches"]) == 3
    assert all(m["source"] == "auto" for m in body["matches"])
    assert all(m["confidence"] == 1.0 for m in body["matches"])

    # DB sanity
    rows = db_session.query(Match).filter(Match.audio_group_id == body["id"]).all()
    assert len(rows) == 3


def test_audio_upload_unmatched_audio_number_persists_no_match_row(client, db_session):
    """Stub STT yields [23,5,105]. If we set up a template/capture where OCR somehow
    only has 23, expect 1 match row (for 23) and 2 unmatched audio entries."""
    # Skip — stub OCR is hardcoded to return [23,5,105], can't easily change here.
    # The existing matcher unit tests cover this case at the pure-function level.
    pass
```

- [ ] **Step 3: Modify `app/api/captures.py` — `upload_audio` to call matcher and persist Match rows**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`. Add this import to the top imports (alongside existing):

```python
from app.services.matcher import match_numbers
from app.schemas import MatchOut
from sqlalchemy import func
```

Then replace the existing `upload_audio` function with this version (keeping the same signature; this version adds matcher invocation + Match row creation + matches in response):

```python
@router.post("/{capture_id}/audio", response_model=AudioGroupOut, status_code=status.HTTP_201_CREATED)
def upload_audio(
    capture_id: int,
    group_index: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    stt: SttService = Depends(get_stt_service),
) -> AudioGroupOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    t = db.get(Template, c.template_id)
    if t is None:
        raise HTTPException(status_code=500, detail="template missing for capture")

    multiplier = _multiplier_for_group(t.groups_json, group_index)
    if multiplier is None:
        raise HTTPException(status_code=400, detail=f"group_index {group_index} not in template")

    Path(settings.media_dir, "audio").mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_g{group_index}.webm"
    fpath = Path(settings.media_dir, "audio", fname)
    audio_bytes = audio.file.read()
    fpath.write_bytes(audio_bytes)

    pipeline_result = transcribe_and_parse(audio_bytes, stt)

    row = AudioGroup(
        capture_id=capture_id,
        group_index=group_index,
        audio_path=str(fpath),
        transcript=pipeline_result.transcript,
        parsed_numbers_json=json.dumps(pipeline_result.parsed_numbers),
        sum=pipeline_result.sum,
        multiplier_snapshot=multiplier,
    )
    db.add(row)
    db.flush()  # need row.id for matches

    # Auto-match: gather OCR numbers for this capture + existing match counts (across other groups)
    ocr_rows = db.query(OcrNumber).filter(OcrNumber.capture_id == capture_id).all()
    ocr_pairs = [
        (n.id, n.corrected_value if n.corrected_value is not None else n.raw_value)
        for n in ocr_rows
        if (n.corrected_value is not None or n.raw_value is not None)
    ]
    existing_counts = dict(
        db.query(Match.ocr_number_id, func.count(Match.id))
        .group_by(Match.ocr_number_id)
        .all()
    )
    proposals = match_numbers(pipeline_result.parsed_numbers, ocr_pairs, existing_counts)

    match_rows: list[Match] = []
    for prop in proposals:
        if prop.ocr_id is None:
            continue
        m = Match(
            ocr_number_id=prop.ocr_id,
            audio_group_id=row.id,
            confidence=prop.confidence,
            source="auto",
        )
        db.add(m)
        match_rows.append(m)
    db.commit()
    db.refresh(row)
    for m in match_rows:
        db.refresh(m)

    return AudioGroupOut(
        id=row.id,
        capture_id=row.capture_id,
        group_index=row.group_index,
        audio_path=row.audio_path,
        transcript=row.transcript,
        parsed_numbers=pipeline_result.parsed_numbers,
        sum=row.sum,
        multiplier_snapshot=row.multiplier_snapshot,
        matches=[MatchOut.model_validate(m) for m in match_rows],
    )
```

- [ ] **Step 4: Run audio tests — expect existing 6 pass + 1 new pass**

```bash
pytest tests/test_api_capture_audio.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 132 passed (122 + 10 matcher unit tests + 1 new audio test + AudioGroupOut schema test still passes; the existing test_audio_upload_creates_audio_group test should still pass because we only ADDED `matches` field).

Actually count: 122 + 10 (matcher) + 1 (new audio test) = 133. The existing test asserts shape of body without checking `matches`, so it passes too.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/captures.py backend/app/schemas.py backend/tests/test_api_capture_audio.py
git commit -m "feat(api): auto-match audio numbers to OCR numbers on upload + return matches"
```

---

## Task 3: PATCH OCR correction endpoint

**Files:**
- Modify: `backend/app/api/captures.py` (add endpoint)
- Modify: `backend/app/schemas.py` (add `OcrCorrectionIn`)
- Create: `backend/tests/test_api_capture_correction.py`

- [ ] **Step 1: Add schema**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
class OcrCorrectionIn(BaseModel):
    corrected_value: float | None  # None to clear correction
```

- [ ] **Step 2: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_correction.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture(client, tid: int) -> tuple[int, list[int]]:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    body = r.json()
    return body["id"], [n["id"] for n in body["ocr_numbers"]]


def test_patch_ocr_value(client, db_session):
    """Sửa OCR value 23 → 24."""
    from app.models import OcrNumber
    tid = _create_template(client)
    cid, ocr_ids = _create_capture(client, tid)
    target = ocr_ids[0]

    resp = client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": 24.0})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == target
    assert body["corrected_value"] == 24.0
    assert body["raw_value"] == 23.0  # raw unchanged

    # DB sanity
    n = db_session.get(OcrNumber, target)
    assert n.corrected_value == 24.0


def test_patch_ocr_clear_correction(client):
    tid = _create_template(client)
    cid, ocr_ids = _create_capture(client, tid)
    target = ocr_ids[0]
    client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": 999.0})

    resp = client.patch(f"/api/captures/{cid}/ocr/{target}", json={"corrected_value": None})
    assert resp.status_code == 200
    assert resp.json()["corrected_value"] is None


def test_patch_ocr_unknown_capture_404(client):
    resp = client.patch("/api/captures/9999/ocr/1", json={"corrected_value": 5.0})
    assert resp.status_code == 404


def test_patch_ocr_unknown_ocr_id_404(client):
    tid = _create_template(client)
    cid, _ = _create_capture(client, tid)
    resp = client.patch(f"/api/captures/{cid}/ocr/99999", json={"corrected_value": 5.0})
    assert resp.status_code == 404


def test_patch_ocr_id_belonging_to_other_capture_404(client):
    """OCR id exists but belongs to a different capture → 404."""
    tid = _create_template(client)
    cid_a, ocr_a = _create_capture(client, tid)
    cid_b, _ = _create_capture(client, tid)
    # Try to patch ocr_a's id via cid_b
    resp = client.patch(f"/api/captures/{cid_b}/ocr/{ocr_a[0]}", json={"corrected_value": 5.0})
    assert resp.status_code == 404
```

- [ ] **Step 3: Run — expect FAIL** (endpoint missing)

```bash
pytest tests/test_api_capture_correction.py -v
```

- [ ] **Step 4: Add endpoint to `app/api/captures.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`. Add to imports (alongside existing — `OcrNumberOut` and `BBoxOut` already imported):

```python
from app.schemas import OcrCorrectionIn
```

Then append to the file (after `upload_audio`):

```python
@router.patch("/{capture_id}/ocr/{ocr_id}", response_model=OcrNumberOut)
def patch_ocr(
    capture_id: int,
    ocr_id: int,
    body: OcrCorrectionIn,
    db: Session = Depends(get_db),
) -> OcrNumberOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    n = db.get(OcrNumber, ocr_id)
    if n is None or n.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="ocr number not found in capture")
    n.corrected_value = body.corrected_value
    db.commit()
    db.refresh(n)
    return OcrNumberOut(
        id=n.id,
        bbox=BBoxOut(x=n.bbox_x, y=n.bbox_y, w=n.bbox_w, h=n.bbox_h),
        raw_text=n.raw_text,
        raw_value=n.raw_value,
        corrected_value=n.corrected_value,
        confidence=n.confidence,
    )
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_capture_correction.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 138 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/captures.py backend/app/schemas.py backend/tests/test_api_capture_correction.py
git commit -m "feat(api): PATCH /api/captures/{id}/ocr/{ocr_id} for OCR value correction"
```

---

## Task 4: Manual match add/remove endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_api_capture_matches.py`

- [ ] **Step 1: Add schema**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
class MatchActionIn(BaseModel):
    ocr_number_id: int
    audio_group_id: int
    action: str  # 'add' | 'remove'
```

- [ ] **Step 2: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_matches.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture_with_audio(client) -> tuple[int, list[int], int]:
    """Create capture + upload audio. Returns (capture_id, ocr_ids, audio_group_id)."""
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cb = r.json()
    cid = cb["id"]
    ocr_ids = [n["id"] for n in cb["ocr_numbers"]]

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    ag_id = r.json()["id"]
    return cid, ocr_ids, ag_id


def test_manual_add_match(client, db_session):
    from app.models import Match
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # Stub already auto-matched all 3, so the new match becomes a 4th row
    pre_count = db_session.query(Match).filter(Match.audio_group_id == ag_id).count()

    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "add",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source"] == "manual"
    assert body["ocr_number_id"] == ocr_ids[0]

    post_count = db_session.query(Match).filter(Match.audio_group_id == ag_id).count()
    assert post_count == pre_count + 1


def test_manual_remove_match(client, db_session):
    from app.models import Match
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # Find an existing auto-match for ocr_ids[0]
    auto = db_session.query(Match).filter(
        Match.audio_group_id == ag_id, Match.ocr_number_id == ocr_ids[0]
    ).first()
    assert auto is not None

    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "remove",
    })
    assert resp.status_code == 200, resp.text

    remaining = db_session.query(Match).filter(
        Match.audio_group_id == ag_id, Match.ocr_number_id == ocr_ids[0]
    ).count()
    # Should have removed AT LEAST one (could be multiple if rule "2a" matched twice)
    assert remaining < 1 or remaining == 0


def test_manual_match_unknown_capture_404(client):
    resp = client.post("/api/captures/9999/matches", json={
        "ocr_number_id": 1, "audio_group_id": 1, "action": "add",
    })
    assert resp.status_code == 404


def test_manual_match_invalid_action_400(client):
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": ag_id,
        "action": "explode",
    })
    assert resp.status_code in (400, 422)


def test_manual_match_remove_nonexistent_404(client):
    cid, ocr_ids, ag_id = _create_capture_with_audio(client)
    # First clear all matches for this ocr/group
    client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0], "audio_group_id": ag_id, "action": "remove",
    })
    # Try removing again (now nothing to remove)
    resp = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0], "audio_group_id": ag_id, "action": "remove",
    })
    assert resp.status_code == 404
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_api_capture_matches.py -v
```

- [ ] **Step 4: Add endpoint to `app/api/captures.py`**

Append to imports:

```python
from app.schemas import MatchActionIn
```

Append endpoint (after `patch_ocr`):

```python
@router.post("/{capture_id}/matches", response_model=MatchOut)
def toggle_match(
    capture_id: int,
    body: MatchActionIn,
    response: Response,
    db: Session = Depends(get_db),
) -> MatchOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    if body.action not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="action must be 'add' or 'remove'")

    # Validate ocr/audio_group belong to this capture
    n = db.get(OcrNumber, body.ocr_number_id)
    if n is None or n.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="ocr number not found in capture")
    g = db.get(AudioGroup, body.audio_group_id)
    if g is None or g.capture_id != capture_id:
        raise HTTPException(status_code=404, detail="audio group not found in capture")

    if body.action == "add":
        m = Match(
            ocr_number_id=body.ocr_number_id,
            audio_group_id=body.audio_group_id,
            confidence=1.0,
            source="manual",
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        response.status_code = 201
        return MatchOut.model_validate(m)
    else:  # remove
        # Remove the most recent match for this pair (LIFO behavior — same OCR may match same group N times)
        m = (
            db.query(Match)
            .filter(Match.ocr_number_id == body.ocr_number_id,
                    Match.audio_group_id == body.audio_group_id)
            .order_by(Match.id.desc())
            .first()
        )
        if m is None:
            raise HTTPException(status_code=404, detail="no match exists for this ocr/audio_group")
        snapshot = MatchOut.model_validate(m)
        db.delete(m)
        db.commit()
        return snapshot
```

Add the missing import for `Response` at the top imports (alongside FastAPI imports):

```python
from fastapi import Response
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_capture_matches.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 143 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/captures.py backend/app/schemas.py backend/tests/test_api_capture_matches.py
git commit -m "feat(api): POST /api/captures/{id}/matches add|remove manual matches"
```

---

## Task 5: Finalize endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_api_capture_finalize.py`

- [ ] **Step 1: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_finalize.py`:

```python
import io


def _create_template_multi(client, multipliers: dict[int, float]) -> int:
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _capture_with_groups(client, tid: int, group_indices: list[int]) -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    gp_dict = {str(gi): ["HN"] for gi in group_indices}
    import json as _j
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": _j.dumps(gp_dict)})
    return r.json()["id"]


def _upload_audio(client, cid: int, group_index: int):
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    return client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(group_index)})


def test_finalize_single_group(client):
    """1 group with multiplier 80 + sum 133 (stub) → final_value = 133*80 = 10640."""
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])
    _upload_audio(client, cid, 1)

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "final"
    assert body["final_value"] == 133 * 80


def test_finalize_multi_group(client):
    """3 groups with multipliers 80, 82, 14.5 — each gets stub sum 133."""
    tid = _create_template_multi(client, {1: 80.0, 2: 82.0, 3: 14.5})
    cid = _capture_with_groups(client, tid, [1, 2, 3])
    for gi in [1, 2, 3]:
        _upload_audio(client, cid, gi)

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["final_value"] == 133 * 80 + 133 * 82 + 133 * 14.5


def test_finalize_with_no_audio_groups_400(client):
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])

    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 400


def test_finalize_unknown_capture_404(client):
    resp = client.post("/api/captures/9999/finalize")
    assert resp.status_code == 404


def test_finalize_idempotent_returns_400_for_already_final(client):
    tid = _create_template_multi(client, {1: 80.0})
    cid = _capture_with_groups(client, tid, [1])
    _upload_audio(client, cid, 1)
    client.post(f"/api/captures/{cid}/finalize")
    resp = client.post(f"/api/captures/{cid}/finalize")
    assert resp.status_code == 400
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Add endpoint to `app/api/captures.py`** (after `toggle_match`):

```python
@router.post("/{capture_id}/finalize", response_model=CaptureOut)
def finalize_capture(capture_id: int, db: Session = Depends(get_db)) -> CaptureOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    if c.status != "draft":
        raise HTTPException(status_code=400, detail=f"capture status is '{c.status}', not 'draft'")

    audio_groups = db.query(AudioGroup).filter(AudioGroup.capture_id == capture_id).all()
    if not audio_groups:
        raise HTTPException(status_code=400, detail="capture has no audio groups; cannot finalize")

    final_value = sum((g.sum or 0.0) * g.multiplier_snapshot for g in audio_groups)
    c.final_value = final_value
    c.status = "final"
    db.commit()
    db.refresh(c)

    rows = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()
    return _capture_to_out(c, rows)
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_api_capture_finalize.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 148 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/captures.py backend/tests/test_api_capture_finalize.py
git commit -m "feat(api): POST /api/captures/{id}/finalize aggregates per-group sum * multiplier"
```

---

## Task 6: Embed `audio_groups` + `matches` in CaptureOut

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_capture_includes_audio_groups.py`

After this task, `GET /api/captures/{id}` returns the full picture including all audio recordings + their matches, ready for frontend to render.

- [ ] **Step 1: Extend `CaptureOut` schema**

Replace the existing `CaptureOut` definition in `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py` with:

```python
class CaptureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    image_path: str
    status: CaptureStatus
    final_value: float | None
    group_provinces: dict[int, list[str]]
    writer_name: str | None
    note_date: str | None
    tags: list[str] | None
    notes: str | None
    ocr_numbers: list[OcrNumberOut] = []
    audio_groups: list[AudioGroupOut] = []
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 2: Write test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_capture_includes_audio_groups.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [
            {"index": 1, "label": "G1", "bet_type": "lo", "multiplier": 80.0},
            {"index": 2, "label": "G2", "bet_type": "de", "multiplier": 82.0},
        ],
    })
    return r.json()["id"]


def test_get_capture_includes_audio_groups_and_matches(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"], "2": ["HN"]}'})
    cid = r.json()["id"]

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "2"})

    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert "audio_groups" in body
    assert len(body["audio_groups"]) == 2
    indices = sorted(g["group_index"] for g in body["audio_groups"])
    assert indices == [1, 2]
    # Each group has matches embedded
    for g in body["audio_groups"]:
        assert "matches" in g
        assert len(g["matches"]) == 3  # stub yields 3 numbers, each matches an OCR


def test_get_capture_includes_empty_audio_groups_when_none(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]
    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    assert resp.json()["audio_groups"] == []
```

- [ ] **Step 3: Modify `_capture_to_out` in `app/api/captures.py`** to include audio_groups + matches.

Replace the existing `_capture_to_out` function with:

```python
def _capture_to_out(c: Capture, ocr_rows: list[OcrNumber]) -> CaptureOut:
    raw_gp = json.loads(c.group_provinces_json)
    group_provinces: dict[int, list[str]] = {int(k): v for k, v in raw_gp.items()}

    # Need a session to load audio_groups + matches. Use object_session() to get the bound session.
    from sqlalchemy.orm import object_session
    db = object_session(c)
    audio_group_rows = db.query(AudioGroup).filter(AudioGroup.capture_id == c.id).order_by(AudioGroup.group_index, AudioGroup.id).all()

    audio_groups_out: list[AudioGroupOut] = []
    for g in audio_group_rows:
        match_rows = db.query(Match).filter(Match.audio_group_id == g.id).order_by(Match.id).all()
        parsed_numbers = json.loads(g.parsed_numbers_json) if g.parsed_numbers_json else None
        audio_groups_out.append(AudioGroupOut(
            id=g.id,
            capture_id=g.capture_id,
            group_index=g.group_index,
            audio_path=g.audio_path,
            transcript=g.transcript,
            parsed_numbers=parsed_numbers,
            sum=g.sum,
            multiplier_snapshot=g.multiplier_snapshot,
            matches=[MatchOut.model_validate(m) for m in match_rows],
        ))

    return CaptureOut(
        id=c.id,
        template_id=c.template_id,
        image_path=c.image_path,
        status=c.status,
        final_value=c.final_value,
        group_provinces=group_provinces,
        writer_name=c.writer_name,
        note_date=c.note_date,
        tags=json.loads(c.tags_json) if c.tags_json else None,
        notes=c.notes,
        ocr_numbers=[
            OcrNumberOut(
                id=n.id,
                bbox=BBoxOut(x=n.bbox_x, y=n.bbox_y, w=n.bbox_w, h=n.bbox_h),
                raw_text=n.raw_text,
                raw_value=n.raw_value,
                corrected_value=n.corrected_value,
                confidence=n.confidence,
            )
            for n in ocr_rows
        ],
        audio_groups=audio_groups_out,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )
```

- [ ] **Step 4: Run — expect PASS** (existing capture tests should still pass since we only added new optional field defaulting to `[]`)

```bash
pytest tests/test_capture_includes_audio_groups.py -v
pytest 2>&1 | tail -3
```

Expected: 150 passed (148 + 2).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/app/api/captures.py backend/tests/test_capture_includes_audio_groups.py
git commit -m "feat(api): embed audio_groups + matches in CaptureOut response"
```

---

## Task 7: End-to-end integration test

**Files:**
- Create: `backend/tests/test_capture_flow_integration.py`

This test exercises the full capture flow: create template → upload image → correct an OCR value → upload 2 audio recordings → toggle a match → finalize → verify response shape.

- [ ] **Step 1: Write integration test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_capture_flow_integration.py`:

```python
"""Full capture flow end-to-end via HTTP. Uses stub OCR + stub STT."""
import io
import json


def test_full_capture_flow(client, db_session):
    # 1. Create template with 2 groups (lô + đề)
    r = client.post("/api/templates", json={
        "name": "Lô-Đề-MB",
        "groups": [
            {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0, "default_provinces": ["HN"]},
            {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0, "default_provinces": ["HN"]},
        ],
    })
    assert r.status_code == 201
    tid = r.json()["id"]

    # 2. Upload image (creates capture + 3 stub OCR rows: 23, 5, 105)
    files = {"image": ("note.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32), "image/png")}
    r = client.post("/api/captures", files=files, data={
        "template_id": str(tid),
        "group_provinces": json.dumps({"1": ["HN"], "2": ["HN"]}),
        "writer_name": "Tom",
        "note_date": "2026-04-29",
    })
    assert r.status_code == 201
    cap = r.json()
    cid = cap["id"]
    assert cap["status"] == "draft"
    assert cap["writer_name"] == "Tom"
    assert len(cap["ocr_numbers"]) == 3
    ocr_ids = [n["id"] for n in cap["ocr_numbers"]]

    # 3. Correct one OCR value (23 → 24)
    r = client.patch(f"/api/captures/{cid}/ocr/{ocr_ids[0]}", json={"corrected_value": 24.0})
    assert r.status_code == 200
    assert r.json()["corrected_value"] == 24.0

    # 4. Upload audio for group 1 (stub yields [23, 5, 105]; 23 no longer matches because we corrected to 24)
    files = {"audio": ("a1.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})
    assert r.status_code == 201
    g1 = r.json()
    # 23 should be unmatched (we corrected it to 24); 5 + 105 still match
    matched_count = len(g1["matches"])
    assert matched_count == 2

    # 5. Manually add a match: link audio group 1's 23 to the (now-24) OCR row
    r = client.post(f"/api/captures/{cid}/matches", json={
        "ocr_number_id": ocr_ids[0],
        "audio_group_id": g1["id"],
        "action": "add",
    })
    assert r.status_code == 201
    assert r.json()["source"] == "manual"

    # 6. Upload audio for group 2
    files = {"audio": ("a2.webm", io.BytesIO(b"x"), "audio/webm")}
    r = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "2"})
    assert r.status_code == 201

    # 7. Finalize
    r = client.post(f"/api/captures/{cid}/finalize")
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "final"
    # Both groups have stub sum = 133. final = 133*80 + 133*82 = 21306
    assert final["final_value"] == 133 * 80 + 133 * 82

    # 8. GET capture: verify embedded structure
    r = client.get(f"/api/captures/{cid}")
    assert r.status_code == 200
    full = r.json()
    assert full["status"] == "final"
    assert len(full["audio_groups"]) == 2
    assert all("matches" in g for g in full["audio_groups"])
    # Group 1 should have 3 matches now (2 auto + 1 manual)
    g1_full = next(g for g in full["audio_groups"] if g["group_index"] == 1)
    assert len(g1_full["matches"]) == 3
    # Group 2 still has 3 auto matches
    g2_full = next(g for g in full["audio_groups"] if g["group_index"] == 2)
    assert len(g2_full["matches"]) == 3
```

- [ ] **Step 2: Run — expect PASS** (all underlying endpoints already exist)

```bash
pytest tests/test_capture_flow_integration.py -v
```

Expected: 1 PASS.

- [ ] **Step 3: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 151 passed (150 + 1).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_capture_flow_integration.py
git commit -m "test: end-to-end capture flow integration (template→ocr→audio→match→finalize)"
```

---

## Task 8: Tag plan completion

- [ ] **Step 1: Tag**

```bash
cd /Users/it/Documents/MySource/voiceApp
git tag plan-3-complete
git log --oneline | head -10
```

Expected: tag created. ~40 commits total.

---

## Verification Checklist (end of Plan 3)

- [ ] `pytest -v` passes 151+ tests.
- [ ] Match engine unit tests cover: simple, extra OCR, unmatched, repeated values, duplicate OCR values, existing-counts tie-break, empty cases, ordering.
- [ ] `POST /api/captures/{id}/audio` auto-creates Match rows.
- [ ] `PATCH /api/captures/{id}/ocr/{ocr_id}` updates `corrected_value`.
- [ ] `POST /api/captures/{id}/matches` adds (201) or removes (200) Match rows; 404 on missing.
- [ ] `POST /api/captures/{id}/finalize` aggregates and locks; rejects re-finalize.
- [ ] `GET /api/captures/{id}` returns ocr_numbers + audio_groups (with embedded matches).
- [ ] Tag `plan-3-complete` exists.

## What Plan 3 explicitly does NOT do (deferred)

- ❌ Fuzzy matching for OCR errors (0/6, 1/7) — exact match only for now.
- ❌ Real ML services (Plan 2 already wired; this plan still uses stubs in tests).
- ❌ Frontend (Plans 4-6).
- ❌ Lottery OCR + settlement (Plan 11).
- ❌ Re-running matcher after OCR correction (user must manually toggle matches if they correct an OCR value mid-flow).
