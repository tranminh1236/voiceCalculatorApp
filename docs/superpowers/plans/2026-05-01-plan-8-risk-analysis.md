# Plan 8 — Risk Analysis (Bet / Payout) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hiển thị bảng risk analysis cho 1 capture: với mỗi số đã đặt cược (mỗi audio number trong từng group), tính `stake × num_provinces`, `payout nếu trúng`, `lãi/lỗ`, `% tỷ trọng vốn`, kèm khuyến nghị `pass`/`take` dựa trên ngưỡng người dùng đặt. Pure logic, không cần lottery data. Toggle on/off trên CaptureDetail.

**Architecture:** Backend pure function `compute_risk(capture, template) → RiskReport` (no DB writes — pure analysis). Endpoint `GET /api/captures/{id}/risk?threshold=...` đọc capture + template + audio_groups, gọi calculator, trả về JSON. Frontend `RiskPanel` component với threshold slider, gọi endpoint, render bảng.

**Tech Stack:** Existing — không thêm dep.

**Spec reference:** [docs/superpowers/specs/...design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §16 (bet_type semantics), §14 Plan 8 row.

**Pre-flight:** Plan 6 complete (tag `plan-6-complete`), 161 backend + 8 frontend tests, 63 commits.

---

## Domain interpretation (chốt cho Plan 8)

Each parsed number in an `AudioGroup` represents **1 cược entry** with:
- **stake** (mức tiền) = `parsed_number_value` (vd `parsed_numbers = [10, 5, 20]` → 3 cược, stake lần lượt 10, 5, 20)
- **multiplier** = `audio_group.multiplier_snapshot` (per group, vd 80 cho lô, 82 cho đề)
- **provinces** = `group_provinces[group_index]` (vd `["HN"]` hay `["DNG", "KH"]`)
- **effective_stake** = `stake × len(provinces)` (mỗi đài cược lại 1 lần)
- **payout_if_hits_one_province** = `stake × multiplier` (chỉ tính 1 đài hit; trường hợp lô kép hay nhiều đài hit thì payout cao hơn — vẫn dùng 1 đài làm baseline an toàn)
- **net_if_hits** = `payout_if_hits_one_province - total_capital` (lãi/lỗ thực)
- **capital_share** = `effective_stake / total_capital`

`total_capital` = Σ effective_stake của TẤT CẢ entries trong tất cả audio_groups của capture.

**Recommendation rule** (mặc định):
- `take` nếu `net_if_hits ≥ threshold` (default threshold = 0, tức ít nhất hòa vốn)
- `pass` nếu `net_if_hits < threshold`

User có thể chỉnh threshold qua query param (vd threshold=10000 → chỉ lấy kèo lãi tối thiểu 10k).

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   └── risk.py             # NEW: pure risk calculator
│   ├── api/
│   │   └── captures.py         # MODIFY: add GET /{id}/risk endpoint
│   └── schemas.py              # MODIFY: add RiskReport, RiskEntry schemas
└── tests/
    ├── test_risk_calculator.py # NEW: ~10 cases
    └── test_api_capture_risk.py # NEW: endpoint smoke tests

frontend/
└── src/
    ├── api/
    │   ├── client.ts           # MODIFY: add getCaptureRisk
    │   └── types.ts            # MODIFY: add RiskReport, RiskEntry types
    ├── hooks/
    │   └── useCapture.ts       # MODIFY: add useCaptureRisk
    ├── components/
    │   └── RiskPanel.tsx       # NEW: toggleable risk analysis table
    └── pages/
        └── CaptureDetail.tsx   # MODIFY: render RiskPanel below FinalizeButton
```

---

## Task 1: Risk calculator (pure function)

**Files:**
- Create: `backend/app/services/risk.py`
- Create: `backend/tests/test_risk_calculator.py`

- [ ] **Step 1: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_risk_calculator.py`:

```python
from app.services.risk import compute_risk, RiskInput, AudioGroupInput


def test_single_group_single_number():
    """1 group × 1 đài × 1 số stake 10 với multiplier 80 → payout 800, capital 10, net +790."""
    inp = RiskInput(
        groups=[
            AudioGroupInput(
                group_index=1,
                multiplier=80.0,
                provinces=["HN"],
                parsed_numbers=[10.0],
            )
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 10.0
    assert len(report.entries) == 1
    e = report.entries[0]
    assert e.group_index == 1
    assert e.stake == 10.0
    assert e.effective_stake == 10.0
    assert e.payout_if_hits == 800.0
    assert e.net_if_hits == 790.0
    assert e.capital_share == 1.0
    assert e.recommendation == "take"


def test_multi_provinces_multiplies_stake():
    """1 group × 2 đài × 1 số stake 10 → effective_stake = 20."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN", "DNG"], parsed_numbers=[10.0])],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 20.0
    assert report.entries[0].effective_stake == 20.0
    # payout still per-province (1 đài hit)
    assert report.entries[0].payout_if_hits == 10.0 * 80.0


def test_pass_when_net_below_threshold():
    """5 stake × 80 multiplier = 400 payout. Capital 5+50=55. Net = 400-55 = 345 (take).
    But add another high-stake group: capital = 55 + 1000 = 1055. Net for the 5-stake = 400 - 1055 = -655 → pass."""
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[5.0, 50.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN"], parsed_numbers=[1000.0]),
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    assert report.total_capital == 5 + 50 + 1000
    by_stake = {e.stake: e for e in report.entries}
    # stake 5: payout 400, net 400 - 1055 = -655 → pass
    assert by_stake[5.0].net_if_hits == 400.0 - 1055.0
    assert by_stake[5.0].recommendation == "pass"
    # stake 50: payout 4000, net 4000 - 1055 = 2945 → take
    assert by_stake[50.0].net_if_hits == 4000.0 - 1055.0
    assert by_stake[50.0].recommendation == "take"
    # stake 1000 in đề×82: payout 82000, net = 82000-1055 = 80945 → take
    assert by_stake[1000.0].net_if_hits == 82000.0 - 1055.0
    assert by_stake[1000.0].recommendation == "take"


def test_threshold_above_zero_makes_more_passes():
    """With threshold=500 and a small bet that nets just +100 → pass."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=10.0, provinces=["HN"], parsed_numbers=[100.0])],
        threshold=500.0,
    )
    report = compute_risk(inp)
    e = report.entries[0]
    assert e.payout_if_hits == 1000.0
    assert e.net_if_hits == 900.0
    assert e.recommendation == "take"  # 900 ≥ 500

    inp2 = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=10.0, provinces=["HN"], parsed_numbers=[100.0])],
        threshold=950.0,
    )
    e2 = compute_risk(inp2).entries[0]
    assert e2.recommendation == "pass"  # 900 < 950


def test_capital_share_sums_to_one():
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 30.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN", "KH"], parsed_numbers=[20.0]),
        ],
        threshold=0.0,
    )
    report = compute_risk(inp)
    total_share = sum(e.capital_share for e in report.entries)
    assert abs(total_share - 1.0) < 1e-9


def test_empty_groups_returns_zero():
    inp = RiskInput(groups=[], threshold=0.0)
    r = compute_risk(inp)
    assert r.total_capital == 0.0
    assert r.entries == []


def test_zero_stake_entry_is_skipped_in_capital_share():
    """A 0-stake entry shouldn't break capital_share computation."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[0.0, 10.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    assert r.total_capital == 10.0
    by_stake = {e.stake: e for e in r.entries}
    assert by_stake[0.0].capital_share == 0.0
    assert by_stake[10.0].capital_share == 1.0


def test_repeated_number_in_group_each_counts_separately():
    """Rule '2a + 2c': same number read twice → 2 separate entries (each with own stake)."""
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 10.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    assert r.total_capital == 20.0
    assert len(r.entries) == 2
    assert all(e.stake == 10.0 for e in r.entries)


def test_entry_order_preserves_group_then_audio_order():
    inp = RiskInput(
        groups=[
            AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 20.0]),
            AudioGroupInput(group_index=2, multiplier=82.0, provinces=["HN"], parsed_numbers=[5.0]),
        ],
        threshold=0.0,
    )
    r = compute_risk(inp)
    # Output entries follow input audio_group order, then audio_index within group
    assert [(e.group_index, e.audio_index, e.stake) for e in r.entries] == [
        (1, 0, 10.0), (1, 1, 20.0), (2, 0, 5.0),
    ]


def test_summary_counts():
    inp = RiskInput(
        groups=[AudioGroupInput(group_index=1, multiplier=80.0, provinces=["HN"], parsed_numbers=[10.0, 5.0])],
        threshold=0.0,
    )
    r = compute_risk(inp)
    # take_count + pass_count == len(entries)
    assert r.take_count + r.pass_count == len(r.entries)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_risk_calculator.py -v
```

- [ ] **Step 3: Implement `app/services/risk.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/risk.py`:

```python
"""Risk analysis: per-bet payout / loss / recommendation.

Pure function: takes a capture's audio groups + multipliers + provinces,
returns a report with one RiskEntry per parsed audio number. No DB, no I/O.

The recommendation logic flags a bet as 'pass' if its net-if-win is below
a user-set threshold (default 0 = at least break even).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioGroupInput:
    group_index: int
    multiplier: float
    provinces: list[str]
    parsed_numbers: list[float]


@dataclass(frozen=True)
class RiskInput:
    groups: list[AudioGroupInput]
    threshold: float = 0.0


@dataclass(frozen=True)
class RiskEntry:
    group_index: int
    audio_index: int               # 0-based position within parsed_numbers
    stake: float                   # raw value from audio
    num_provinces: int
    effective_stake: float         # stake × num_provinces
    multiplier: float
    payout_if_hits: float          # stake × multiplier (per single-province hit)
    net_if_hits: float             # payout_if_hits - total_capital
    capital_share: float           # effective_stake / total_capital (0..1)
    recommendation: str            # 'take' | 'pass'


@dataclass(frozen=True)
class RiskReport:
    total_capital: float
    threshold: float
    entries: list[RiskEntry]
    take_count: int
    pass_count: int


def compute_risk(inp: RiskInput) -> RiskReport:
    # Phase 1: compute total_capital
    total_capital = 0.0
    for g in inp.groups:
        n_prov = len(g.provinces)
        for stake in g.parsed_numbers:
            total_capital += stake * n_prov

    # Phase 2: build entries
    entries: list[RiskEntry] = []
    for g in inp.groups:
        n_prov = len(g.provinces)
        for idx, stake in enumerate(g.parsed_numbers):
            effective = stake * n_prov
            payout = stake * g.multiplier  # per single-province hit
            net = payout - total_capital
            share = effective / total_capital if total_capital > 0 else 0.0
            rec = "take" if net >= inp.threshold else "pass"
            entries.append(RiskEntry(
                group_index=g.group_index,
                audio_index=idx,
                stake=stake,
                num_provinces=n_prov,
                effective_stake=effective,
                multiplier=g.multiplier,
                payout_if_hits=payout,
                net_if_hits=net,
                capital_share=share,
                recommendation=rec,
            ))

    take_count = sum(1 for e in entries if e.recommendation == "take")
    pass_count = sum(1 for e in entries if e.recommendation == "pass")
    return RiskReport(
        total_capital=total_capital,
        threshold=inp.threshold,
        entries=entries,
        take_count=take_count,
        pass_count=pass_count,
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_risk_calculator.py -v
```

Expected: 9 PASS.

- [ ] **Step 5: Run full backend suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 170 passed (161 + 9).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/risk.py backend/tests/test_risk_calculator.py
git commit -m "feat(risk): pure compute_risk() with per-entry payout/net/share/recommendation"
```

---

## Task 2: Risk endpoint + Pydantic schemas

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_api_capture_risk.py`

- [ ] **Step 1: Add Pydantic schemas**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
class RiskEntryOut(BaseModel):
    group_index: int
    audio_index: int
    stake: float
    num_provinces: int
    effective_stake: float
    multiplier: float
    payout_if_hits: float
    net_if_hits: float
    capital_share: float
    recommendation: str


class RiskReportOut(BaseModel):
    capture_id: int
    total_capital: float
    threshold: float
    take_count: int
    pass_count: int
    entries: list[RiskEntryOut]
```

- [ ] **Step 2: Write endpoint tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_risk.py`:

```python
import io
import json


def _create_template(client, multipliers: dict[int, float]) -> int:
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _create_capture_with_audio(client, multipliers: dict[int, float], group_provinces: dict[int, list[str]]):
    tid = _create_template(client, multipliers)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    gp_str = json.dumps({str(k): v for k, v in group_provinces.items()})
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": gp_str})
    cid = r.json()["id"]
    for gi in multipliers.keys():
        files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
        client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(gi)})
    return cid


def test_risk_basic(client):
    """Stub STT yields parsed_numbers=[23,5,105]. With multiplier 80, 1 đài HN:
    capital = 23+5+105 = 133. payout per number = stake × 80.
    Entries: 23 → payout 1840, net 1707, take. 5 → payout 400, net 267, take. 105 → payout 8400, net 8267, take.
    """
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["HN"]})
    resp = client.get(f"/api/captures/{cid}/risk")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["capture_id"] == cid
    assert body["total_capital"] == 133.0
    assert body["threshold"] == 0.0
    assert len(body["entries"]) == 3
    by_stake = {e["stake"]: e for e in body["entries"]}
    assert by_stake[23.0]["payout_if_hits"] == 1840.0
    assert by_stake[23.0]["recommendation"] == "take"
    assert body["take_count"] == 3
    assert body["pass_count"] == 0


def test_risk_with_threshold(client):
    """High threshold should flip some takes to passes."""
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["HN"]})
    # threshold=2000: 23 → net 1707 < 2000 → pass; 5 → net 267 → pass; 105 → net 8267 → take
    resp = client.get(f"/api/captures/{cid}/risk?threshold=2000")
    assert resp.status_code == 200
    body = resp.json()
    assert body["threshold"] == 2000.0
    by_stake = {e["stake"]: e for e in body["entries"]}
    assert by_stake[23.0]["recommendation"] == "pass"
    assert by_stake[5.0]["recommendation"] == "pass"
    assert by_stake[105.0]["recommendation"] == "take"
    assert body["take_count"] == 1
    assert body["pass_count"] == 2


def test_risk_multi_province_doubles_capital(client):
    """provinces=[DNG,KH] → effective_stake doubles for that group."""
    cid = _create_capture_with_audio(client, {1: 80.0}, {1: ["DNG", "KH"]})
    resp = client.get(f"/api/captures/{cid}/risk")
    body = resp.json()
    assert body["total_capital"] == 133.0 * 2
    assert all(e["num_provinces"] == 2 for e in body["entries"])
    assert all(e["effective_stake"] == e["stake"] * 2 for e in body["entries"])


def test_risk_unknown_capture_404(client):
    resp = client.get("/api/captures/9999/risk")
    assert resp.status_code == 404


def test_risk_capture_with_no_audio_returns_empty(client):
    """Capture with no audio → empty entries, capital 0."""
    tid = _create_template(client, {1: 80.0})
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]

    resp = client.get(f"/api/captures/{cid}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_capital"] == 0.0
    assert body["entries"] == []
```

- [ ] **Step 3: Run — expect FAIL**

- [ ] **Step 4: Add endpoint to `app/api/captures.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`. Add imports near top (next to existing):

```python
from fastapi import Query
from app.services.risk import compute_risk, RiskInput, AudioGroupInput
from app.schemas import RiskReportOut, RiskEntryOut
```

Append endpoint at the end of the file:

```python
@router.get("/{capture_id}/risk", response_model=RiskReportOut)
def get_capture_risk(
    capture_id: int,
    threshold: float = Query(default=0.0),
    db: Session = Depends(get_db),
) -> RiskReportOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    group_provinces_raw = json.loads(c.group_provinces_json)
    group_provinces = {int(k): v for k, v in group_provinces_raw.items()}

    audio_rows = db.query(AudioGroup).filter(AudioGroup.capture_id == capture_id).order_by(
        AudioGroup.group_index, AudioGroup.id
    ).all()

    inputs: list[AudioGroupInput] = []
    for g in audio_rows:
        parsed = json.loads(g.parsed_numbers_json) if g.parsed_numbers_json else []
        inputs.append(AudioGroupInput(
            group_index=g.group_index,
            multiplier=g.multiplier_snapshot,
            provinces=group_provinces.get(g.group_index, []),
            parsed_numbers=parsed,
        ))

    report = compute_risk(RiskInput(groups=inputs, threshold=threshold))
    return RiskReportOut(
        capture_id=capture_id,
        total_capital=report.total_capital,
        threshold=report.threshold,
        take_count=report.take_count,
        pass_count=report.pass_count,
        entries=[RiskEntryOut(**e.__dict__) for e in report.entries],
    )
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_capture_risk.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 175 passed (170 + 5).

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/schemas.py backend/app/api/captures.py backend/tests/test_api_capture_risk.py
git commit -m "feat(api): GET /api/captures/{id}/risk?threshold= returns per-entry risk report"
```

---

## Task 3: Frontend — types + API client + hook

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/hooks/useCapture.ts`

- [ ] **Step 1: Add types**

Append to `/Users/it/Documents/MySource/voiceApp/frontend/src/api/types.ts`:

```ts
export interface RiskEntry {
  group_index: number
  audio_index: number
  stake: number
  num_provinces: number
  effective_stake: number
  multiplier: number
  payout_if_hits: number
  net_if_hits: number
  capital_share: number
  recommendation: 'take' | 'pass'
}

export interface RiskReport {
  capture_id: number
  total_capital: number
  threshold: number
  take_count: number
  pass_count: number
  entries: RiskEntry[]
}
```

- [ ] **Step 2: Add API call**

Append to `/Users/it/Documents/MySource/voiceApp/frontend/src/api/client.ts` (after `deleteCapture`):

```ts
import type { RiskReport } from './types'

export async function getCaptureRisk(captureId: number, threshold: number = 0): Promise<RiskReport> {
  const r = await api.get<RiskReport>(`/captures/${captureId}/risk`, { params: { threshold } })
  return r.data
}
```

(If `RiskReport` type import already added at top via the existing big import, no need to duplicate. But the existing top import block in `client.ts` doesn't include RiskReport — append it cleanly.)

Cleaner: edit the top-of-file import block in client.ts. Find the line:

```ts
import type { Template, Capture, Province, GroupDef, AudioGroup, OcrNumber, MatchRecord } from './types'
```

Replace with:

```ts
import type { Template, Capture, Province, GroupDef, AudioGroup, OcrNumber, MatchRecord, RiskReport } from './types'
```

Then at the end of file just add the `getCaptureRisk` function (no separate import).

- [ ] **Step 3: Add hook**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/hooks/useCapture.ts`. Update the top import (add `getCaptureRisk`):

```ts
import {
  getCapture,
  patchOcr,
  uploadAudio,
  toggleMatch,
  finalizeCapture,
  patchCaptureMetadata,
  getCaptureRisk,
  type CaptureMetadataInput,
} from '../api/client'
```

Append at the end of the file:

```ts
export function useCaptureRisk(captureId: number | null, threshold: number) {
  return useQuery({
    queryKey: ['capture-risk', captureId, threshold],
    queryFn: () => getCaptureRisk(captureId as number, threshold),
    enabled: captureId !== null,
  })
}
```

- [ ] **Step 4: Verify build + tests**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
npm test
```

Expected: clean build; 8 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/hooks/useCapture.ts
git commit -m "feat(frontend): RiskReport types + getCaptureRisk client + useCaptureRisk hook"
```

---

## Task 4: RiskPanel component

**Files:**
- Create: `frontend/src/components/RiskPanel.tsx`

- [ ] **Step 1: Create `frontend/src/components/RiskPanel.tsx`**

```tsx
import { useState } from 'react'
import { useCaptureRisk } from '../hooks/useCapture'

interface Props {
  captureId: number
}

const PRESETS = [0, 100_000, 500_000, 1_000_000]

export default function RiskPanel({ captureId }: Props) {
  const [threshold, setThreshold] = useState(0)
  const { data: report, isLoading, error } = useCaptureRisk(captureId, threshold)

  return (
    <div className="bg-slate-800 p-3 rounded space-y-3">
      <div className="flex justify-between items-baseline flex-wrap gap-2">
        <h3 className="font-semibold">Risk analysis</h3>
        {report && (
          <span className="text-sm text-slate-400">
            Vốn: <strong className="text-slate-200">{report.total_capital.toLocaleString()}</strong>
            {' · '}
            <span className="text-emerald-400">{report.take_count} take</span>
            {' / '}
            <span className="text-rose-400">{report.pass_count} pass</span>
          </span>
        )}
      </div>

      <div className="flex gap-2 items-center flex-wrap">
        <label className="text-sm text-slate-400">Ngưỡng lãi tối thiểu:</label>
        <input
          type="number"
          step="1000"
          className="px-2 py-1 rounded bg-slate-700 text-white w-32"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
        />
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setThreshold(p)}
            className={`px-2 py-1 text-xs rounded ${threshold === p ? 'bg-sky-600' : 'bg-slate-700'}`}
          >
            {p === 0 ? 'hòa vốn' : p.toLocaleString()}
          </button>
        ))}
      </div>

      {isLoading && <div className="text-slate-400 text-sm">Đang tính...</div>}
      {error && <div className="text-red-400 text-sm">{(error as Error).message}</div>}

      {report && report.entries.length === 0 && (
        <div className="text-slate-400 text-sm">Chưa có audio group nào — chưa tính được risk.</div>
      )}

      {report && report.entries.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs">
              <tr>
                <th className="text-left py-1">Group</th>
                <th className="text-right py-1">Stake</th>
                <th className="text-right py-1">×Đài</th>
                <th className="text-right py-1">Eff.</th>
                <th className="text-right py-1">×Mult</th>
                <th className="text-right py-1">Payout</th>
                <th className="text-right py-1">Net nếu trúng</th>
                <th className="text-right py-1">% vốn</th>
                <th className="text-center py-1">Khuyến nghị</th>
              </tr>
            </thead>
            <tbody>
              {report.entries.map((e, i) => (
                <tr key={i} className="border-t border-slate-700">
                  <td className="py-1">G{e.group_index}</td>
                  <td className="text-right py-1">{e.stake.toLocaleString()}</td>
                  <td className="text-right py-1">{e.num_provinces}</td>
                  <td className="text-right py-1">{e.effective_stake.toLocaleString()}</td>
                  <td className="text-right py-1">×{e.multiplier}</td>
                  <td className="text-right py-1">{e.payout_if_hits.toLocaleString()}</td>
                  <td className={
                    'text-right py-1 ' +
                    (e.net_if_hits >= 0 ? 'text-emerald-400' : 'text-rose-400')
                  }>
                    {e.net_if_hits >= 0 ? '+' : ''}{e.net_if_hits.toLocaleString()}
                  </td>
                  <td className="text-right py-1">{(e.capital_share * 100).toFixed(1)}%</td>
                  <td className="text-center py-1">
                    <span className={
                      'px-2 py-0.5 rounded text-xs ' +
                      (e.recommendation === 'take' ? 'bg-emerald-900 text-emerald-300' : 'bg-rose-900 text-rose-300')
                    }>
                      {e.recommendation.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/RiskPanel.tsx
git commit -m "feat(frontend): RiskPanel with threshold slider + per-entry breakdown table"
```

---

## Task 5: Wire RiskPanel into CaptureDetail with toggle

**Files:**
- Modify: `frontend/src/pages/CaptureDetail.tsx`

- [ ] **Step 1: Update `frontend/src/pages/CaptureDetail.tsx`**

Add import:

```tsx
import RiskPanel from '../components/RiskPanel'
```

Inside the component body (after existing `useState` declarations), add:

```tsx
  const [showRisk, setShowRisk] = useState(false)
```

In the JSX, after `<FinalizeButton capture={capture} />` and BEFORE `<CaptureMetadataForm capture={capture} />`, insert:

```tsx
      <div className="bg-slate-800 p-3 rounded">
        <button
          type="button"
          onClick={() => setShowRisk((s) => !s)}
          className="text-sm text-slate-300 hover:text-white"
        >
          {showRisk ? '▼ Risk analysis' : '▶ Risk analysis'}
        </button>
      </div>
      {showRisk && <RiskPanel captureId={capture.id} />}
```

- [ ] **Step 2: Verify build + tests**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
npm test
```

Expected: clean build; 8 tests pass.

- [ ] **Step 3: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/pages/CaptureDetail.tsx
git commit -m "feat(frontend): collapsible RiskPanel on CaptureDetail (toggle)"
```

---

## Task 6: Browser E2E + tag

This task is for the human / assistant operating Playwright. Subagents skip this.

- [ ] **Step 1: Start servers**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null; sleep 2
cd /Users/it/Documents/MySource/voiceApp/backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 > /tmp/voiceapp-be.log 2>&1 &
sleep 4
cd /Users/it/Documents/MySource/voiceApp/frontend && npm run dev > /tmp/voiceapp-fe.log 2>&1 &
sleep 5
```

- [ ] **Step 2: Browser walk-through**

Open `http://localhost:5173/captures/5` (or any capture with audio):

1. Scroll to "Risk analysis" toggle button.
2. Click → table appears with 3 rows (stub yields 23+5+105).
3. Verify columns: Group=G1, Stake/Eff/Payout/Net/% match expected math.
4. Click "500.000" preset → recommendations shift (some pass).
5. Type a custom threshold → table updates.
6. Click toggle again → panel collapses.

- [ ] **Step 3: Stop + tag**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null
cd /Users/it/Documents/MySource/voiceApp
git tag plan-8-complete
git log --oneline | head -10
```

---

## Verification Checklist

- [ ] Backend: 175 tests pass.
- [ ] Frontend: 8 tests pass + clean build.
- [ ] `GET /api/captures/{id}/risk?threshold=N` returns per-entry RiskReport.
- [ ] Risk math verified: payout = stake × multiplier; net = payout − total_capital; capital_share sums to 1.
- [ ] Threshold influences recommendation (take/pass).
- [ ] CaptureDetail has collapsible Risk panel.
- [ ] Tag `plan-8-complete` exists.

## What Plan 8 explicitly does NOT do (deferred)

- ❌ Múi (lô kép — số trùng đuôi xuất hiện nhiều lần) — chỉ tính 1-province-hit baseline. Real settlement payout (with multi-province + lô kép) là Plan 11 settlement engine.
- ❌ Lưu risk recommendation vào DB — pure on-demand compute.
- ❌ Lottery OCR (Plan 11).
- ❌ Historical ROI / win-rate analysis (Plan 10).
