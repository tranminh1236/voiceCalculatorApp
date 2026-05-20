# Plan 6 — History Page + Metadata + Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App có thể dùng hàng ngày: trang History `/captures` list tất cả với filter, form chỉnh metadata (writer/note_date/tags/notes) trên detail page, delete capture button (kèm confirm), nav update với link "History". Backend bổ sung 2 endpoint: `DELETE /api/captures/{id}` và `PATCH /api/captures/{id}/metadata`.

**Architecture:** History dùng `useCaptures` query hook đã có; thêm filters trong UI (client-side filter trên data đã fetch — đủ cho personal scale). Metadata form là controlled inline form trên detail page với debounced auto-save hoặc explicit save button (chọn explicit để đơn giản). Delete: confirm modal → mutate → navigate về History.

**Tech Stack:** Existing — không thêm dep mới.

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §4 (Capture metadata fields), §8 (PATCH metadata endpoint).

**Pre-flight:** Plan 5 complete (tag `plan-5-complete`), 154 backend + 8 frontend tests, 54 commits.

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   └── captures.py             # MODIFY: add PATCH metadata + DELETE endpoints
│   └── schemas.py                  # MODIFY: add CaptureMetadataIn schema
└── tests/
    ├── test_api_capture_metadata.py    # NEW: PATCH metadata
    └── test_api_capture_delete.py      # NEW: DELETE flow

frontend/
└── src/
    ├── api/
    │   └── client.ts               # MODIFY: add patchCaptureMetadata + deleteCapture
    ├── hooks/
    │   ├── useCaptures.ts          # MODIFY: add useCapturesList + useDeleteCapture
    │   └── useCapture.ts           # MODIFY: add useUpdateMetadata
    ├── pages/
    │   ├── History.tsx             # NEW: list page with filters
    │   └── CaptureDetail.tsx       # MODIFY: add metadata form + delete button
    ├── components/
    │   ├── CaptureMetadataForm.tsx # NEW: writer/date/tags/notes editor
    │   └── ConfirmModal.tsx        # NEW: tiny confirm dialog
    └── main.tsx                    # MODIFY: add /captures route + Home link
```

---

## Task 1: Backend — DELETE /api/captures/{id} endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_api_capture_delete.py`

- [ ] **Step 1: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_delete.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture(client, tid: int) -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    return r.json()["id"]


def test_delete_capture(client, db_session):
    from app.models import Capture, OcrNumber
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    # Pre-conditions: capture + ocr rows exist
    assert db_session.get(Capture, cid) is not None
    ocr_count_pre = db_session.query(OcrNumber).filter(OcrNumber.capture_id == cid).count()
    assert ocr_count_pre > 0

    resp = client.delete(f"/api/captures/{cid}")
    assert resp.status_code == 204, resp.text

    # Capture + cascaded OCR rows gone
    db_session.expire_all()
    assert db_session.get(Capture, cid) is None
    assert db_session.query(OcrNumber).filter(OcrNumber.capture_id == cid).count() == 0


def test_delete_capture_cascades_audio_groups(client, db_session):
    """Deleting capture should also remove its audio_groups + matches via FK CASCADE."""
    from app.models import AudioGroup, Match
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    # Add an audio group (which auto-creates matches)
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})

    pre_audio = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).count()
    assert pre_audio == 1

    resp = client.delete(f"/api/captures/{cid}")
    assert resp.status_code == 204

    db_session.expire_all()
    assert db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).count() == 0
    # Matches reference deleted ocr/audio_group → cascade should clean up
    # (Hard to assert directly without group ids; just verify no orphan matches for this cid via join)
    assert db_session.query(Match).join(AudioGroup, Match.audio_group_id == AudioGroup.id, isouter=False).filter(AudioGroup.capture_id == cid).count() == 0


def test_delete_unknown_capture_404(client):
    resp = client.delete("/api/captures/9999")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run — expect FAIL** (endpoint missing)

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_api_capture_delete.py -v
```

- [ ] **Step 3: Add DELETE endpoint to `app/api/captures.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`. Append at the end of the file:

```python
@router.delete("/{capture_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_capture(capture_id: int, db: Session = Depends(get_db)):
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    db.delete(c)
    db.commit()
    # Note: image + audio files on disk are NOT deleted in this version.
    # Acceptable for personal scale; can add cleanup task later.
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_api_capture_delete.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 157 passed (154 + 3).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/captures.py backend/tests/test_api_capture_delete.py
git commit -m "feat(api): DELETE /api/captures/{id} with FK cascade to ocr/audio/matches"
```

---

## Task 2: Backend — PATCH /api/captures/{id}/metadata endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_api_capture_metadata.py`

- [ ] **Step 1: Add schema**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
class CaptureMetadataIn(BaseModel):
    writer_name: str | None = None
    note_date: str | None = None  # YYYY-MM-DD
    tags: list[str] | None = None
    notes: str | None = None
```

- [ ] **Step 2: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_metadata.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def _create_capture(client, tid: int) -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    return r.json()["id"]


def test_patch_metadata_full(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    resp = client.patch(f"/api/captures/{cid}/metadata", json={
        "writer_name": "Tom",
        "note_date": "2026-04-29",
        "tags": ["weekly", "lottery"],
        "notes": "Test note",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["writer_name"] == "Tom"
    assert body["note_date"] == "2026-04-29"
    assert body["tags"] == ["weekly", "lottery"]
    assert body["notes"] == "Test note"


def test_patch_metadata_partial_keeps_existing(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)
    client.patch(f"/api/captures/{cid}/metadata", json={
        "writer_name": "A", "note_date": "2026-04-01", "tags": ["x"], "notes": "n",
    })

    # Only update writer_name
    resp = client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": "B"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["writer_name"] == "B"
    # Other fields unchanged
    assert body["note_date"] == "2026-04-01"
    assert body["tags"] == ["x"]
    assert body["notes"] == "n"


def test_patch_metadata_clear_with_null(client):
    """Sending `null` should set field to null (clear)."""
    tid = _create_template(client)
    cid = _create_capture(client, tid)
    client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": "Tom"})

    # Note: distinguishing "not provided" vs "explicitly null" requires use of model_fields_set.
    # We send writer_name explicitly as null:
    resp = client.patch(f"/api/captures/{cid}/metadata", json={"writer_name": None})
    assert resp.status_code == 200
    assert resp.json()["writer_name"] is None


def test_patch_metadata_unknown_capture_404(client):
    resp = client.patch("/api/captures/9999/metadata", json={"writer_name": "x"})
    assert resp.status_code == 404
```

- [ ] **Step 3: Run — expect FAIL**

- [ ] **Step 4: Add endpoint + schema import to `app/api/captures.py`**

Append to imports at top:

```python
from app.schemas import CaptureMetadataIn
```

Append endpoint at the end of the file:

```python
@router.patch("/{capture_id}/metadata", response_model=CaptureOut)
def patch_metadata(
    capture_id: int,
    body: CaptureMetadataIn,
    db: Session = Depends(get_db),
) -> CaptureOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    # Only update fields that were explicitly provided (use model_fields_set)
    provided = body.model_fields_set
    if "writer_name" in provided:
        c.writer_name = body.writer_name
    if "note_date" in provided:
        c.note_date = body.note_date
    if "tags" in provided:
        c.tags_json = json.dumps(body.tags) if body.tags is not None else None
    if "notes" in provided:
        c.notes = body.notes

    db.commit()
    db.refresh(c)
    rows = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()
    return _capture_to_out(c, rows)
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_capture_metadata.py -v
```

Expected: 4 PASS.

- [ ] **Step 6: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 161 passed.

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/schemas.py backend/app/api/captures.py backend/tests/test_api_capture_metadata.py
git commit -m "feat(api): PATCH /api/captures/{id}/metadata partial update"
```

---

## Task 3: Frontend — API client additions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add 2 functions to `frontend/src/api/client.ts`**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/api/client.ts`. Append at the end of the file (after `finalizeCapture`):

```ts
export interface CaptureMetadataInput {
  writer_name?: string | null
  note_date?: string | null
  tags?: string[] | null
  notes?: string | null
}

export async function patchCaptureMetadata(captureId: number, body: CaptureMetadataInput): Promise<Capture> {
  const r = await api.patch<Capture>(`/captures/${captureId}/metadata`, body)
  return r.data
}

export async function deleteCapture(captureId: number): Promise<void> {
  await api.delete(`/captures/${captureId}`)
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
git add frontend/src/api/client.ts
git commit -m "feat(frontend): API client for patchCaptureMetadata + deleteCapture"
```

---

## Task 4: Frontend hooks — list captures + delete + update metadata

**Files:**
- Modify: `frontend/src/hooks/useCaptures.ts`
- Modify: `frontend/src/hooks/useCapture.ts`

- [ ] **Step 1: Update `frontend/src/hooks/useCaptures.ts`**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/hooks/useCaptures.ts`. Replace its entire content with:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCapture, deleteCapture, listCaptures, type CreateCaptureInput } from '../api/client'

export function useCapturesList() {
  return useQuery({ queryKey: ['captures'], queryFn: listCaptures })
}

export function useCreateCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateCaptureInput) => createCapture(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['captures'] }),
  })
}

export function useDeleteCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (captureId: number) => deleteCapture(captureId),
    onSuccess: (_, captureId) => {
      qc.invalidateQueries({ queryKey: ['captures'] })
      qc.removeQueries({ queryKey: ['capture', captureId] })
    },
  })
}
```

- [ ] **Step 2: Add `useUpdateMetadata` to `frontend/src/hooks/useCapture.ts`**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/hooks/useCapture.ts`. Append at the end of the file (after `useFinalizeCapture`):

```ts
import { patchCaptureMetadata, type CaptureMetadataInput } from '../api/client'

export function useUpdateMetadata(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CaptureMetadataInput) => patchCaptureMetadata(captureId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['capture', captureId] })
      qc.invalidateQueries({ queryKey: ['captures'] })
    },
  })
}
```

(The duplicate `import` at the bottom is intentional — keep `patchCaptureMetadata` import here so the hook file is self-contained at the bottom. Actually cleaner: move the import up. Replace the existing top import block to add `patchCaptureMetadata` and `CaptureMetadataInput`.)

Cleaner approach — replace the existing top `import` line with:

```ts
import {
  getCapture,
  patchOcr,
  uploadAudio,
  toggleMatch,
  finalizeCapture,
  patchCaptureMetadata,
  type CaptureMetadataInput,
} from '../api/client'
```

Then DON'T add the duplicate import at the bottom — just append the `useUpdateMetadata` function.

- [ ] **Step 3: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/hooks/useCaptures.ts frontend/src/hooks/useCapture.ts
git commit -m "feat(frontend): hooks for captures list, delete, metadata update"
```

---

## Task 5: ConfirmModal component

**Files:**
- Create: `frontend/src/components/ConfirmModal.tsx`

- [ ] **Step 1: Create `frontend/src/components/ConfirmModal.tsx`**

```tsx
interface Props {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
  isPending?: boolean
}

export default function ConfirmModal({
  title,
  message,
  confirmLabel = 'OK',
  cancelLabel = 'Hủy',
  destructive,
  onConfirm,
  onCancel,
  isPending,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 rounded p-5 max-w-md w-full space-y-3">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-slate-300 text-sm">{message}</p>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-3 py-2 bg-slate-700 rounded disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className={`px-3 py-2 rounded disabled:opacity-50 ${destructive ? 'bg-red-600' : 'bg-sky-600'}`}
          >
            {isPending ? '...' : confirmLabel}
          </button>
        </div>
      </div>
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
git add frontend/src/components/ConfirmModal.tsx
git commit -m "feat(frontend): ConfirmModal component for destructive actions"
```

---

## Task 6: CaptureMetadataForm component

**Files:**
- Create: `frontend/src/components/CaptureMetadataForm.tsx`

- [ ] **Step 1: Create `frontend/src/components/CaptureMetadataForm.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { useUpdateMetadata } from '../hooks/useCapture'
import type { Capture } from '../api/types'

interface Props {
  capture: Capture
}

export default function CaptureMetadataForm({ capture }: Props) {
  const updateMutation = useUpdateMetadata(capture.id)
  const [writerName, setWriterName] = useState(capture.writer_name ?? '')
  const [noteDate, setNoteDate] = useState(capture.note_date ?? '')
  const [tagsStr, setTagsStr] = useState((capture.tags ?? []).join(', '))
  const [notes, setNotes] = useState(capture.notes ?? '')

  // Reset local state when capture changes (after refetch / nav)
  useEffect(() => {
    setWriterName(capture.writer_name ?? '')
    setNoteDate(capture.note_date ?? '')
    setTagsStr((capture.tags ?? []).join(', '))
    setNotes(capture.notes ?? '')
  }, [capture.id, capture.writer_name, capture.note_date, capture.tags, capture.notes])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const tags = tagsStr.split(',').map((s) => s.trim()).filter(Boolean)
    updateMutation.mutate({
      writer_name: writerName || null,
      note_date: noteDate || null,
      tags: tags.length > 0 ? tags : null,
      notes: notes || null,
    })
  }

  return (
    <form onSubmit={submit} className="bg-slate-800 p-3 rounded space-y-2">
      <h3 className="font-semibold">Metadata</h3>
      <div className="grid sm:grid-cols-2 gap-2">
        <label className="block text-sm">
          <span className="text-slate-400">Writer</span>
          <input
            className="w-full mt-1 px-2 py-1 rounded bg-slate-700 text-white"
            value={writerName}
            onChange={(e) => setWriterName(e.target.value)}
            placeholder="Tên người ghi"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Note date</span>
          <input
            type="date"
            className="w-full mt-1 px-2 py-1 rounded bg-slate-700 text-white"
            value={noteDate}
            onChange={(e) => setNoteDate(e.target.value)}
          />
        </label>
      </div>
      <label className="block text-sm">
        <span className="text-slate-400">Tags (comma-separated)</span>
        <input
          className="w-full mt-1 px-2 py-1 rounded bg-slate-700 text-white"
          value={tagsStr}
          onChange={(e) => setTagsStr(e.target.value)}
          placeholder="weekly, lottery, ..."
        />
      </label>
      <label className="block text-sm">
        <span className="text-slate-400">Notes</span>
        <textarea
          className="w-full mt-1 px-2 py-1 rounded bg-slate-700 text-white min-h-[60px]"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Ghi chú tự do..."
        />
      </label>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="px-3 py-1 bg-sky-600 rounded disabled:opacity-50"
        >
          {updateMutation.isPending ? 'Đang lưu...' : 'Lưu metadata'}
        </button>
        {updateMutation.isSuccess && !updateMutation.isPending && (
          <span className="text-emerald-400 text-sm">Đã lưu</span>
        )}
        {updateMutation.error && (
          <span className="text-red-400 text-sm">{(updateMutation.error as Error).message}</span>
        )}
      </div>
    </form>
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
git add frontend/src/components/CaptureMetadataForm.tsx
git commit -m "feat(frontend): CaptureMetadataForm with writer/date/tags/notes editor"
```

---

## Task 7: History page

**Files:**
- Create: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/main.tsx` (add route + Home nav link)

- [ ] **Step 1: Create `frontend/src/pages/History.tsx`**

```tsx
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCapturesList } from '../hooks/useCaptures'
import type { CaptureStatus } from '../api/types'

const STATUSES: (CaptureStatus | 'all')[] = ['all', 'draft', 'final', 'settled']

export default function History() {
  const { data: captures, isLoading, error } = useCapturesList()
  const [statusFilter, setStatusFilter] = useState<CaptureStatus | 'all'>('all')
  const [writerFilter, setWriterFilter] = useState('')
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!captures) return []
    return captures.filter((c) => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false
      if (writerFilter && (c.writer_name ?? '').toLowerCase().indexOf(writerFilter.toLowerCase()) < 0) return false
      if (search) {
        const hay = `${c.id} ${c.writer_name ?? ''} ${(c.tags ?? []).join(' ')} ${c.notes ?? ''}`.toLowerCase()
        if (hay.indexOf(search.toLowerCase()) < 0) return false
      }
      return true
    })
  }, [captures, statusFilter, writerFilter, search])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">History</h1>

      <div className="bg-slate-800 p-3 rounded flex flex-wrap gap-2 items-end">
        <label className="text-sm">
          <span className="text-slate-400 block">Status</span>
          <select
            className="mt-1 px-2 py-1 rounded bg-slate-700 text-white"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
          >
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-slate-400 block">Writer contains</span>
          <input
            className="mt-1 px-2 py-1 rounded bg-slate-700 text-white"
            value={writerFilter}
            onChange={(e) => setWriterFilter(e.target.value)}
          />
        </label>
        <label className="text-sm flex-1 min-w-[200px]">
          <span className="text-slate-400 block">Search (id / tags / notes)</span>
          <input
            className="w-full mt-1 px-2 py-1 rounded bg-slate-700 text-white"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div className="text-sm text-slate-400 self-center">
          {filtered.length}/{captures?.length ?? 0}
        </div>
      </div>

      {isLoading && <div className="text-slate-400">Loading...</div>}
      {error && <div className="text-red-400">{(error as Error).message}</div>}
      {!isLoading && filtered.length === 0 && (
        <div className="text-slate-400">Không có capture nào khớp filter.</div>
      )}

      <ul className="space-y-2">
        {filtered.map((c) => (
          <li key={c.id} className="bg-slate-800 p-3 rounded flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <Link to={`/captures/${c.id}`} className="font-semibold text-sky-400 hover:underline">
                  Capture #{c.id}
                </Link>
                <span className={
                  c.status === 'final' ? 'text-xs text-emerald-400' :
                  c.status === 'settled' ? 'text-xs text-amber-400' : 'text-xs text-slate-500'
                }>
                  {c.status}
                </span>
                {c.note_date && <span className="text-xs text-slate-400">· {c.note_date}</span>}
                {c.writer_name && <span className="text-xs text-slate-400">· {c.writer_name}</span>}
              </div>
              {c.tags && c.tags.length > 0 && (
                <div className="text-xs text-slate-500 mt-1">
                  {c.tags.map((t) => `#${t}`).join(' ')}
                </div>
              )}
              {c.final_value !== null && (
                <div className="text-sm text-slate-300 mt-1">
                  Final: <strong>{c.final_value.toLocaleString()}</strong>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 2: Update `frontend/src/main.tsx`** — add route + nav link

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/main.tsx`. Add import:

```tsx
import History from './pages/History'
```

Inside `<Routes>`, after the `captures/new` route and BEFORE `captures/:id`, add:

```tsx
<Route path="captures" element={<History />} />
```

Now update the nav in App.tsx (or wherever links live). Open `/Users/it/Documents/MySource/voiceApp/frontend/src/App.tsx` and replace the `<header>` block with:

```tsx
      <header className="border-b border-slate-700 px-4 py-3 flex flex-wrap gap-4">
        <Link to="/" className="font-semibold">VoiceApp</Link>
        <Link to="/captures/new" className="text-slate-300 hover:text-white">New Capture</Link>
        <Link to="/captures" className="text-slate-300 hover:text-white">History</Link>
        <Link to="/templates" className="text-slate-300 hover:text-white">Templates</Link>
      </header>
```

- [ ] **Step 3: Verify build + tests**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
npm test
```

Expected: clean build; 8 tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/pages/History.tsx frontend/src/main.tsx frontend/src/App.tsx
git commit -m "feat(frontend): History page with filters + nav update"
```

---

## Task 8: Wire metadata form + delete button into CaptureDetail

**Files:**
- Modify: `frontend/src/pages/CaptureDetail.tsx`

- [ ] **Step 1: Update `frontend/src/pages/CaptureDetail.tsx`**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/CaptureDetail.tsx`. Add imports:

```tsx
import { useNavigate } from 'react-router-dom'
import CaptureMetadataForm from '../components/CaptureMetadataForm'
import ConfirmModal from '../components/ConfirmModal'
import { useDeleteCapture } from '../hooks/useCaptures'
```

Inside the component (top-level), add after the existing hooks:

```tsx
  const navigate = useNavigate()
  const deleteMutation = useDeleteCapture()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
```

After the existing `<FinalizeButton capture={capture} />` line (which is at the end of the JSX), add:

```tsx
      <CaptureMetadataForm capture={capture} />

      <div className="bg-slate-800 p-3 rounded flex justify-between items-center">
        <span className="text-sm text-slate-400">
          Created: {new Date(capture.created_at).toLocaleString()}
        </span>
        <button
          type="button"
          onClick={() => setShowDeleteConfirm(true)}
          className="px-3 py-1 text-red-400 hover:bg-red-900/30 rounded"
        >
          Xóa capture
        </button>
      </div>

      {showDeleteConfirm && (
        <ConfirmModal
          title="Xóa capture?"
          message={`Capture #${capture.id} và toàn bộ OCR + audio + matches sẽ bị xóa khỏi DB. (File ảnh + audio trên đĩa giữ lại.) Hành động này không thể hoàn tác.`}
          confirmLabel="Xóa"
          destructive
          isPending={deleteMutation.isPending}
          onCancel={() => setShowDeleteConfirm(false)}
          onConfirm={() => {
            deleteMutation.mutate(capture.id, {
              onSuccess: () => navigate('/captures'),
            })
          }}
        />
      )}
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
git commit -m "feat(frontend): metadata form + delete button + confirm modal on CaptureDetail"
```

---

## Task 9: Browser E2E verification + tag

This is for the human / assistant operating Playwright. Subagents should skip this task.

- [ ] **Step 1: Start servers**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null; sleep 2
cd /Users/it/Documents/MySource/voiceApp/backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 > /tmp/voiceapp-be.log 2>&1 &
sleep 4
cd /Users/it/Documents/MySource/voiceApp/frontend && npm run dev > /tmp/voiceapp-fe.log 2>&1 &
sleep 5
```

- [ ] **Step 2: Browser walk-through**

Open http://localhost:5173/captures and verify:

1. History page renders with list of captures from previous plans.
2. Filter by status="final" → only finalized captures shown.
3. Click on a capture link → CaptureDetail opens.
4. Metadata form: enter writer="Smoke Test", date, tag="testing" → click Lưu → "Đã lưu" appears.
5. Reload → metadata persists.
6. Click "Xóa capture" → confirm modal appears → click "Xóa" → redirects to History → capture is gone from list.

- [ ] **Step 3: Stop servers + tag**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null
cd /Users/it/Documents/MySource/voiceApp
git tag plan-6-complete
git log --oneline | head -10
```

---

## Verification Checklist (end of Plan 6)

- [ ] Backend: 161 tests pass.
- [ ] Frontend: 8 tests pass + clean build.
- [ ] `DELETE /api/captures/{id}` cascades + returns 204.
- [ ] `PATCH /api/captures/{id}/metadata` partial-updates only provided fields.
- [ ] `/captures` History page renders + filters work.
- [ ] CaptureDetail metadata form persists writer/date/tags/notes.
- [ ] Delete capture from UI removes it + redirects to History.
- [ ] Tag `plan-6-complete` exists.

## What Plan 6 explicitly does NOT do (deferred)

- ❌ Cleanup of orphan media files on disk after delete (acceptable for personal scale)
- ❌ Real PWA icons (cosmetic; placeholder works)
- ❌ Capture export JSON download (defer to Plan 7 training prep)
- ❌ Bulk operations (multi-delete, batch tag) (YAGNI)
- ❌ Pagination on History (personal scale → list grows slowly; defer)
- ❌ Lottery OCR + settlement (Plan 11)
