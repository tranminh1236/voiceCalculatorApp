# Plan 5 — Annotation UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện UX 1 capture đầy đủ: trang detail (`/captures/:id`) hiển thị image + bbox overlay, click bbox để sửa OCR value, panel cho mỗi group có audio recorder + auto-match + tô màu match trên image, finalize button + hiển thị `final_value`. Sau khi NewCapture upload xong sẽ redirect sang detail. Cuối plan: 1 user có thể hoàn thành 1 capture đầy đủ qua UI mà không cần curl.

**Architecture:** Trang detail tự refetch capture qua TanStack Query sau mọi mutation (correction, audio upload, match toggle, finalize). OCR overlay là `<canvas>` overlay trên `<img>`, vẽ bbox rectangle với màu (xanh = chưa match, các màu khác per-group). Click bbox → modal/inline input. Group panel cho từng group ở template: hiện multiplier, audio recorder, transcript + parsed numbers + sum sau khi upload.

**Tech Stack:** Existing — React + Tailwind + TanStack Query. Image rendering native `<img>` + canvas overlay. Không cần lib mới.

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §5 (user flow 1 capture), §7 (frontend components).

**Pre-flight:** Plan 4 complete (tag `plan-4-complete`), 152 backend + 8 frontend tests, 46 commits.

---

## File Structure

```
frontend/
└── src/
    ├── api/
    │   └── client.ts                    # MODIFY: add getImageURL helper
    ├── hooks/
    │   ├── useCapture.ts                # NEW: query single capture by id + mutations
    │   └── useCaptures.ts               # MODIFY: add finalize mutation
    ├── components/
    │   ├── AudioRecorder.tsx            # MODIFY (was placeholder): real impl with start/stop UI
    │   ├── OcrOverlay.tsx               # MODIFY (was placeholder): canvas overlay with bbox + click handler
    │   ├── GroupPanel.tsx               # NEW: per-group audio recorder + matches display
    │   ├── OcrCorrectionInput.tsx       # NEW: inline input modal/dropdown for editing OCR value
    │   └── FinalizeButton.tsx           # NEW: finalize action + display final_value
    ├── pages/
    │   ├── CaptureDetail.tsx            # NEW: full capture editing UI
    │   └── NewCapture.tsx               # MODIFY: redirect to /captures/:id after create
    └── main.tsx                         # MODIFY: add /captures/:id route
```

**Responsibilities:**
- `OcrOverlay.tsx` — pure presentation: take image URL + ocr_numbers + per-ocr color/state → render. Calls `onOcrClick(ocr_id)` when bbox is clicked.
- `OcrCorrectionInput.tsx` — controlled inline editor; emits `onSave(value | null)`.
- `AudioRecorder.tsx` — uses `useRecorder`; emits `onComplete(blob)` when user finishes.
- `GroupPanel.tsx` — state machine: idle → recording → uploading → done; shows transcript + parsed numbers + sum + matches.
- `CaptureDetail.tsx` — orchestrator: image+overlay on left, group panels stacked on right, finalize button at bottom.

---

## Task 1: useCapture hook + CaptureDetail skeleton + route

**Files:**
- Create: `frontend/src/hooks/useCapture.ts`
- Create: `frontend/src/pages/CaptureDetail.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/src/hooks/useCapture.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getCapture,
  patchOcr,
  uploadAudio,
  toggleMatch,
  finalizeCapture,
} from '../api/client'

export function useCapture(captureId: number | null) {
  return useQuery({
    queryKey: ['capture', captureId],
    queryFn: () => getCapture(captureId as number),
    enabled: captureId !== null,
  })
}

export function usePatchOcr(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ocrId, value }: { ocrId: number; value: number | null }) =>
      patchOcr(captureId, ocrId, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useUploadAudio(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ groupIndex, audio }: { groupIndex: number; audio: Blob }) =>
      uploadAudio(captureId, groupIndex, audio),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useToggleMatch(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      ocr_number_id: number
      audio_group_id: number
      action: 'add' | 'remove'
    }) => toggleMatch(captureId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useFinalizeCapture(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => finalizeCapture(captureId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}
```

- [ ] **Step 2: Create `frontend/src/pages/CaptureDetail.tsx`** (minimal skeleton — content fleshed out in later tasks)

```tsx
import { useParams } from 'react-router-dom'
import { useCapture } from '../hooks/useCapture'

export default function CaptureDetail() {
  const { id } = useParams<{ id: string }>()
  const captureId = id ? parseInt(id) : null
  const { data: capture, isLoading, error } = useCapture(captureId)

  if (isLoading) return <div className="text-slate-300">Loading...</div>
  if (error) return <div className="text-red-400">{(error as Error).message}</div>
  if (!capture) return <div className="text-slate-400">Not found</div>

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Capture #{capture.id}</h1>
        <span className={
          capture.status === 'final' ? 'text-emerald-400' :
          capture.status === 'settled' ? 'text-amber-400' : 'text-slate-400'
        }>
          status: {capture.status}
        </span>
      </div>

      <div className="text-sm text-slate-400">
        Template #{capture.template_id} · {capture.ocr_numbers.length} OCR · {capture.audio_groups.length} audio groups
        {capture.final_value !== null && <> · final: <strong>{capture.final_value.toLocaleString()}</strong></>}
      </div>

      {/* OCR overlay + group panels rendered in subsequent tasks */}
      <pre className="text-xs bg-slate-800 p-2 rounded overflow-auto max-h-96">
        {JSON.stringify({ ocr_numbers: capture.ocr_numbers, audio_groups: capture.audio_groups }, null, 2)}
      </pre>
    </div>
  )
}
```

- [ ] **Step 3: Update `frontend/src/main.tsx`** — add route + import

Add import at the top:

```tsx
import CaptureDetail from './pages/CaptureDetail'
```

Inside `<Routes>`, add a new `<Route>` AFTER the `captures/new` route:

```tsx
<Route path="captures/:id" element={<CaptureDetail />} />
```

- [ ] **Step 4: Verify build + tests**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
npm test
```

Expected: clean build; 8 tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/hooks/useCapture.ts frontend/src/pages/CaptureDetail.tsx frontend/src/main.tsx
git commit -m "feat(frontend): CaptureDetail page skeleton + useCapture mutation hooks"
```

---

## Task 2: Image-serving endpoint on backend + getImageURL helper

CaptureDetail needs to display the captured image. Backend currently stores image at `data/media/captures/<uuid>.png` but doesn't serve it. We need a static-file endpoint.

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_static_media.py`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Write failing test on backend**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_static_media.py`:

```python
import io


def test_can_fetch_uploaded_image(client):
    """After POST /api/captures, the saved image should be retrievable via /media/captures/<filename>."""
    # Create template + capture
    r = client.post("/api/templates", json={
        "name": "T", "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    tid = r.json()["id"]

    img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {"image": ("test.png", io.BytesIO(img_bytes), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cap = r.json()
    img_path = cap["image_path"]
    # img_path is absolute filesystem path; we need just the filename
    fname = img_path.split("/")[-1]

    resp = client.get(f"/media/captures/{fname}")
    assert resp.status_code == 200
    assert resp.content.startswith(b"\x89PNG")


def test_unknown_media_404(client):
    resp = client.get("/media/captures/does-not-exist.png")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run — expect FAIL** (no media route)

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_static_media.py -v
```

- [ ] **Step 3: Mount static files in `app/main.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/main.py`. Add this import at the top (alongside existing FastAPI imports):

```python
from fastapi.staticfiles import StaticFiles
```

Inside `create_app()`, AFTER `app.add_middleware(CORSMiddleware, ...)` and BEFORE the `@app.get("/api/health")` decorator, add:

```python
    # Serve uploaded media (images + audio) — read-only
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
```

Note: `Path` and `settings` are already imported in `main.py`.

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_static_media.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Run full backend suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 154 passed (152 + 2).

- [ ] **Step 6: Update frontend `api/client.ts` — add `getImageURL` helper**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/api/client.ts`. After the `import` block (right before `const baseURL = ...`), add:

```ts
function backendOrigin(): string {
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (!envBase || envBase.startsWith('/')) {
    // proxied through vite — same origin
    return ''
  }
  // strip trailing /api if present
  return envBase.replace(/\/api\/?$/, '')
}
```

Then at the END of the file, add:

```ts
/**
 * Convert a backend image_path (absolute filesystem path on the server)
 * into a URL the browser can fetch via the /media static mount.
 */
export function getImageURL(imagePath: string): string {
  // image_path looks like /Users/.../backend/data/media/captures/<uuid>.png
  // Extract everything after "/media/" → "captures/<uuid>.png"
  const idx = imagePath.indexOf('/media/')
  if (idx === -1) return imagePath
  const rel = imagePath.slice(idx + '/media/'.length)
  return `${backendOrigin()}/media/${rel}`
}
```

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/main.py backend/tests/test_static_media.py frontend/src/api/client.ts
git commit -m "feat(backend): serve uploaded media via /media static mount + frontend getImageURL helper"
```

---

## Task 3: OCR overlay canvas component

**Files:**
- Replace: `frontend/src/components/OcrOverlay.tsx`

Component: render image, draw bbox rectangles using HTML canvas overlay positioned absolutely on top. Click on bbox → `onOcrClick(ocr_id)`. Color per OCR number (passed in via prop).

- [ ] **Step 1: Replace `frontend/src/components/OcrOverlay.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'
import type { OcrNumber } from '../api/types'

export interface OcrOverlayProps {
  imageUrl: string
  ocrNumbers: OcrNumber[]
  /** Map ocr_id → color string; OCR not in map renders default (slate). */
  colorByOcrId?: Record<number, string>
  onOcrClick?: (ocrId: number) => void
  /** Highlighted OCR id (e.g. currently being edited) */
  highlightedOcrId?: number | null
}

interface ImageDims {
  natural: { w: number; h: number }
  rendered: { w: number; h: number }
}

const DEFAULT_COLOR = 'rgba(148, 163, 184, 0.85)' // slate-400
const HIGHLIGHT_COLOR = 'rgba(250, 204, 21, 1)' // yellow-400

export default function OcrOverlay(props: OcrOverlayProps) {
  const { imageUrl, ocrNumbers, colorByOcrId, onOcrClick, highlightedOcrId } = props
  const imgRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [dims, setDims] = useState<ImageDims | null>(null)

  // Recompute dims on image load + window resize
  useEffect(() => {
    const updateDims = () => {
      const img = imgRef.current
      if (!img || !img.naturalWidth) return
      setDims({
        natural: { w: img.naturalWidth, h: img.naturalHeight },
        rendered: { w: img.clientWidth, h: img.clientHeight },
      })
    }
    updateDims()
    window.addEventListener('resize', updateDims)
    return () => window.removeEventListener('resize', updateDims)
  }, [imageUrl])

  // Draw bboxes
  useEffect(() => {
    if (!dims) return
    const canvas = canvasRef.current
    if (!canvas) return
    canvas.width = dims.rendered.w
    canvas.height = dims.rendered.h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const sx = dims.rendered.w / dims.natural.w
    const sy = dims.rendered.h / dims.natural.h

    for (const n of ocrNumbers) {
      const x = n.bbox.x * sx
      const y = n.bbox.y * sy
      const w = n.bbox.w * sx
      const h = n.bbox.h * sy
      const isHighlighted = highlightedOcrId === n.id
      ctx.strokeStyle = isHighlighted ? HIGHLIGHT_COLOR : (colorByOcrId?.[n.id] ?? DEFAULT_COLOR)
      ctx.lineWidth = isHighlighted ? 3 : 2
      ctx.strokeRect(x, y, w, h)

      // Label with current value
      const value = n.corrected_value ?? n.raw_value
      const label = value === null ? '?' : String(value)
      ctx.fillStyle = isHighlighted ? HIGHLIGHT_COLOR : (colorByOcrId?.[n.id] ?? DEFAULT_COLOR)
      ctx.font = '14px system-ui, sans-serif'
      const textW = ctx.measureText(label).width
      ctx.fillRect(x, y - 18, textW + 8, 18)
      ctx.fillStyle = '#0f172a'
      ctx.fillText(label, x + 4, y - 4)
    }
  }, [dims, ocrNumbers, colorByOcrId, highlightedOcrId])

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onOcrClick || !dims) return
    const rect = canvasRef.current!.getBoundingClientRect()
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    const sx = dims.rendered.w / dims.natural.w
    const sy = dims.rendered.h / dims.natural.h

    // Find topmost bbox containing the click
    for (let i = ocrNumbers.length - 1; i >= 0; i--) {
      const n = ocrNumbers[i]
      const x = n.bbox.x * sx
      const y = n.bbox.y * sy
      const w = n.bbox.w * sx
      const h = n.bbox.h * sy
      if (cx >= x && cx <= x + w && cy >= y && cy <= y + h) {
        onOcrClick(n.id)
        return
      }
    }
  }

  return (
    <div className="relative inline-block">
      <img
        ref={imgRef}
        src={imageUrl}
        alt="capture"
        className="max-w-full rounded"
        onLoad={() => {
          // Trigger a re-measure after natural dimensions are available
          const img = imgRef.current
          if (img) {
            setDims({
              natural: { w: img.naturalWidth, h: img.naturalHeight },
              rendered: { w: img.clientWidth, h: img.clientHeight },
            })
          }
        }}
      />
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className="absolute top-0 left-0 cursor-crosshair"
      />
    </div>
  )
}
```

- [ ] **Step 2: Render in CaptureDetail**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/CaptureDetail.tsx`. Add imports at top:

```tsx
import OcrOverlay from '../components/OcrOverlay'
import { getImageURL } from '../api/client'
```

Replace the `<pre>` debug block in the return statement with:

```tsx
      <div className="grid lg:grid-cols-2 gap-4">
        <div>
          <OcrOverlay
            imageUrl={getImageURL(capture.image_path)}
            ocrNumbers={capture.ocr_numbers}
          />
        </div>
        <div className="text-xs">
          <details className="bg-slate-800 p-2 rounded">
            <summary className="cursor-pointer">Raw JSON (debug)</summary>
            <pre className="overflow-auto max-h-96">{JSON.stringify({
              ocr_numbers: capture.ocr_numbers,
              audio_groups: capture.audio_groups,
            }, null, 2)}</pre>
          </details>
        </div>
      </div>
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/OcrOverlay.tsx frontend/src/pages/CaptureDetail.tsx
git commit -m "feat(frontend): OcrOverlay canvas with bbox rendering + click detection"
```

---

## Task 4: OCR correction inline editor

**Files:**
- Create: `frontend/src/components/OcrCorrectionInput.tsx`
- Modify: `frontend/src/pages/CaptureDetail.tsx`

- [ ] **Step 1: Create `frontend/src/components/OcrCorrectionInput.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'

interface Props {
  initialValue: number | null
  onSave: (value: number | null) => void
  onCancel: () => void
  isPending?: boolean
}

export default function OcrCorrectionInput({ initialValue, onSave, onCancel, isPending }: Props) {
  const [value, setValue] = useState<string>(initialValue === null ? '' : String(initialValue))
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed === '') {
      onSave(null)
      return
    }
    const num = Number(trimmed)
    if (Number.isFinite(num)) {
      onSave(num)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-center bg-slate-800 p-2 rounded">
      <input
        ref={inputRef}
        type="number"
        step="any"
        className="px-2 py-1 rounded bg-slate-700 text-white w-32"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isPending}
      />
      <button type="submit" disabled={isPending} className="px-3 py-1 bg-emerald-600 rounded disabled:opacity-50">
        Lưu
      </button>
      <button type="button" onClick={onCancel} disabled={isPending} className="px-3 py-1 bg-slate-700 rounded">
        Hủy
      </button>
      <button
        type="button"
        onClick={() => onSave(null)}
        disabled={isPending}
        className="px-3 py-1 text-slate-400 hover:text-red-400"
        title="Xóa correction (về raw value)"
      >
        Xóa
      </button>
    </form>
  )
}
```

- [ ] **Step 2: Wire into CaptureDetail**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/CaptureDetail.tsx`. Add imports at top:

```tsx
import { useState } from 'react'
import OcrCorrectionInput from '../components/OcrCorrectionInput'
import { usePatchOcr } from '../hooks/useCapture'
```

Inside the `CaptureDetail` function body, BEFORE the `if (isLoading)` line, add:

```tsx
  const [editingOcrId, setEditingOcrId] = useState<number | null>(null)
  const patchMutation = usePatchOcr(captureId ?? 0)
```

Then replace the OcrOverlay invocation with:

```tsx
          <OcrOverlay
            imageUrl={getImageURL(capture.image_path)}
            ocrNumbers={capture.ocr_numbers}
            highlightedOcrId={editingOcrId}
            onOcrClick={(id) => setEditingOcrId(id)}
          />
          {editingOcrId !== null && (
            <div className="mt-2">
              <div className="text-sm text-slate-400 mb-1">Sửa OCR #{editingOcrId}</div>
              <OcrCorrectionInput
                initialValue={
                  capture.ocr_numbers.find((n) => n.id === editingOcrId)?.corrected_value ??
                  capture.ocr_numbers.find((n) => n.id === editingOcrId)?.raw_value ??
                  null
                }
                isPending={patchMutation.isPending}
                onSave={(v) => {
                  patchMutation.mutate(
                    { ocrId: editingOcrId, value: v },
                    { onSuccess: () => setEditingOcrId(null) }
                  )
                }}
                onCancel={() => setEditingOcrId(null)}
              />
            </div>
          )}
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/OcrCorrectionInput.tsx frontend/src/pages/CaptureDetail.tsx
git commit -m "feat(frontend): inline OCR value correction (click bbox → edit → PATCH)"
```

---

## Task 5: AudioRecorder UI component

**Files:**
- Create (replace if exists): `frontend/src/components/AudioRecorder.tsx`

- [ ] **Step 1: Create `frontend/src/components/AudioRecorder.tsx`**

```tsx
import { useEffect } from 'react'
import { useRecorder } from '../hooks/useRecorder'

interface Props {
  /** Called once when user stops recording and a blob is available. */
  onComplete: (audio: Blob) => void
  /** Disable while parent is uploading. */
  busy?: boolean
}

export default function AudioRecorder({ onComplete, busy }: Props) {
  const { start, stop, isRecording, blob, error, reset } = useRecorder()

  // Auto-emit when blob lands, then reset
  useEffect(() => {
    if (blob) {
      onComplete(blob)
      reset()
    }
  }, [blob, onComplete, reset])

  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        {!isRecording ? (
          <button
            type="button"
            onClick={start}
            disabled={busy}
            className="px-4 py-2 bg-rose-600 rounded disabled:opacity-50 flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-white"></span>
            Ghi âm
          </button>
        ) : (
          <button
            type="button"
            onClick={stop}
            className="px-4 py-2 bg-slate-700 rounded flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
            Đang ghi... (bấm để dừng)
          </button>
        )}
        {busy && <span className="text-slate-400 text-sm">Đang upload + STT...</span>}
      </div>
      {error && <div className="text-red-400 text-sm">{error}</div>}
    </div>
  )
}
```

- [ ] **Step 2: Verify build (no integration yet — Task 6 wires it in)**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 3: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/AudioRecorder.tsx
git commit -m "feat(frontend): AudioRecorder component with start/stop UI + auto-emit on blob"
```

---

## Task 6: GroupPanel + integrate into CaptureDetail

**Files:**
- Create: `frontend/src/components/GroupPanel.tsx`
- Modify: `frontend/src/pages/CaptureDetail.tsx`

- [ ] **Step 1: Create `frontend/src/components/GroupPanel.tsx`**

```tsx
import AudioRecorder from './AudioRecorder'
import type { AudioGroup, GroupDef, OcrNumber } from '../api/types'

interface Props {
  groupDef: GroupDef
  audioGroups: AudioGroup[]  // recordings already made for this group_index (can be 0+)
  ocrNumbers: OcrNumber[]    // for resolving match → value
  onRecord: (audio: Blob) => void
  uploading?: boolean
}

export default function GroupPanel({ groupDef, audioGroups, ocrNumbers, onRecord, uploading }: Props) {
  const ocrById = new Map(ocrNumbers.map((n) => [n.id, n]))

  return (
    <div className="bg-slate-800 p-3 rounded space-y-3">
      <div className="flex justify-between items-baseline">
        <h3 className="font-semibold">
          {groupDef.label}
          <span className="text-xs text-slate-400 ml-2">
            ({groupDef.bet_type} × {groupDef.multiplier})
          </span>
        </h3>
        <div className="text-xs text-slate-400">
          {audioGroups.length} bản ghi
        </div>
      </div>

      <AudioRecorder onComplete={onRecord} busy={uploading} />

      {audioGroups.map((g) => (
        <div key={g.id} className="border-t border-slate-700 pt-2 text-sm space-y-1">
          {g.transcript && (
            <div className="text-slate-300">
              <span className="text-slate-500">Transcript:</span> {g.transcript}
            </div>
          )}
          {g.parsed_numbers && (
            <div className="text-slate-300">
              <span className="text-slate-500">Numbers:</span>{' '}
              {g.parsed_numbers.join(' + ')} ={' '}
              <strong>{g.sum?.toLocaleString() ?? '—'}</strong>
            </div>
          )}
          <div className="text-xs text-slate-400">
            {g.matches.length} match{g.matches.length !== 1 ? 'es' : ''}:{' '}
            {g.matches.map((m) => {
              const n = ocrById.get(m.ocr_number_id)
              const val = n ? (n.corrected_value ?? n.raw_value) : '?'
              return `${val}(${m.source[0]})`
            }).join(', ')}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Wire GroupPanels + match coloring into CaptureDetail**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/CaptureDetail.tsx`. Add imports:

```tsx
import GroupPanel from '../components/GroupPanel'
import { useUploadAudio } from '../hooks/useCapture'
import { useTemplates } from '../hooks/useTemplates'
```

Inside `CaptureDetail`, AFTER the `patchMutation` line, add:

```tsx
  const uploadAudio = useUploadAudio(captureId ?? 0)
  const { data: templates } = useTemplates()
  const template = templates?.find((t) => t.id === capture?.template_id)
```

Move that `template` lookup AFTER the early-return checks (since `capture` may be null). The cleanest approach is to compute template inside the JSX — actually, since hooks must run unconditionally, keep them at top, but reference `capture?.template_id`. The lookup with `templates?.find` is safe.

Build a `colorByOcrId` map (rotate distinct colors per group_index):

```tsx
  const GROUP_COLORS = ['#22d3ee', '#a78bfa', '#f472b6', '#facc15', '#34d399']  // cyan, violet, pink, yellow, emerald
  const colorByOcrId: Record<number, string> = {}
  if (capture) {
    for (const ag of capture.audio_groups) {
      const color = GROUP_COLORS[(ag.group_index - 1) % GROUP_COLORS.length]
      for (const m of ag.matches) {
        colorByOcrId[m.ocr_number_id] = color
      }
    }
  }
```

Pass `colorByOcrId` to OcrOverlay. Replace the OcrOverlay invocation with the prop added:

```tsx
          <OcrOverlay
            imageUrl={getImageURL(capture.image_path)}
            ocrNumbers={capture.ocr_numbers}
            colorByOcrId={colorByOcrId}
            highlightedOcrId={editingOcrId}
            onOcrClick={(id) => setEditingOcrId(id)}
          />
```

Then in the right column (replace the `<details>` debug block with GroupPanels):

```tsx
        <div className="space-y-3">
          {template?.groups.map((g) => {
            const recordings = capture.audio_groups.filter((ag) => ag.group_index === g.index)
            return (
              <GroupPanel
                key={g.index}
                groupDef={g}
                audioGroups={recordings}
                ocrNumbers={capture.ocr_numbers}
                uploading={uploadAudio.isPending}
                onRecord={(blob) => uploadAudio.mutate({ groupIndex: g.index, audio: blob })}
              />
            )
          })}
          {!template && <div className="text-slate-400">Loading template...</div>}
          {uploadAudio.error && (
            <div className="text-red-400 text-sm">{(uploadAudio.error as Error).message}</div>
          )}
        </div>
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/GroupPanel.tsx frontend/src/pages/CaptureDetail.tsx
git commit -m "feat(frontend): GroupPanel with audio recorder + match list + per-group bbox coloring"
```

---

## Task 7: Finalize button + result display + redirect from NewCapture

**Files:**
- Create: `frontend/src/components/FinalizeButton.tsx`
- Modify: `frontend/src/pages/CaptureDetail.tsx`
- Modify: `frontend/src/pages/NewCapture.tsx`

- [ ] **Step 1: Create `frontend/src/components/FinalizeButton.tsx`**

```tsx
import { useFinalizeCapture } from '../hooks/useCapture'
import type { Capture } from '../api/types'

interface Props {
  capture: Capture
}

export default function FinalizeButton({ capture }: Props) {
  const finalizeMutation = useFinalizeCapture(capture.id)

  if (capture.status !== 'draft') {
    return (
      <div className="bg-emerald-900/40 border border-emerald-700 p-3 rounded">
        <div className="text-sm text-slate-300">Capture đã được finalize.</div>
        <div className="text-xl font-bold mt-1">
          Final value: {capture.final_value?.toLocaleString() ?? '—'}
        </div>
      </div>
    )
  }

  const canFinalize = capture.audio_groups.length > 0

  return (
    <div className="space-y-2">
      <button
        onClick={() => finalizeMutation.mutate()}
        disabled={!canFinalize || finalizeMutation.isPending}
        className="px-4 py-2 bg-emerald-600 rounded disabled:opacity-50"
      >
        {finalizeMutation.isPending ? 'Đang finalize...' : 'Finalize'}
      </button>
      {!canFinalize && (
        <div className="text-sm text-slate-400">Cần ghi âm ít nhất 1 group trước khi finalize.</div>
      )}
      {finalizeMutation.error && (
        <div className="text-red-400 text-sm">{(finalizeMutation.error as Error).message}</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Render in CaptureDetail**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/CaptureDetail.tsx`. Add import:

```tsx
import FinalizeButton from '../components/FinalizeButton'
```

At the very end of the JSX (after the `<div className="grid lg:grid-cols-2 gap-4">...</div>` closing), add:

```tsx
      <FinalizeButton capture={capture} />
```

- [ ] **Step 3: Update NewCapture to redirect after capture create**

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/pages/NewCapture.tsx`. Add import:

```tsx
import { useNavigate } from 'react-router-dom'
```

Inside the component (top-level), add:

```tsx
  const navigate = useNavigate()
```

Replace the `onCapture` function body:

```tsx
  const onCapture = async (blob: Blob) => {
    if (!templateId) return
    const cap = await createMutation.mutateAsync({
      template_id: templateId,
      group_provinces: groupProvinces,
      image: blob,
    })
    navigate(`/captures/${cap.id}`)
  }
```

You can also remove the `result` state, the `setResult(cap)` line, and the entire `{result && ...}` block that displayed the OCR results — they're now shown on the detail page.

Specifically:
- Remove `import type { Capture } from '../api/types'` if no longer needed
- Remove `const [result, setResult] = useState<Capture | null>(null)`
- Remove the entire `{result && (...)}` JSX block at the bottom

- [ ] **Step 4: Verify build + tests**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
npm test
```

Expected: clean build, 8 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/FinalizeButton.tsx frontend/src/pages/CaptureDetail.tsx frontend/src/pages/NewCapture.tsx
git commit -m "feat(frontend): FinalizeButton on detail page + auto-redirect from NewCapture after upload"
```

---

## Task 8: End-to-end browser verification + tag

This task uses Playwright (the assistant's MCP integration) to validate the full flow programmatically. The assistant should already have Playwright MCP available.

- [ ] **Step 1: Start backend + frontend dev servers**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null; sleep 2
cd /Users/it/Documents/MySource/voiceApp/backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 > /tmp/voiceapp-be.log 2>&1 &
sleep 4
cd /Users/it/Documents/MySource/voiceApp/frontend && npm run dev > /tmp/voiceapp-fe.log 2>&1 &
sleep 5
curl -s http://localhost:8000/api/health
curl -sI http://localhost:5173 | head -1
```

- [ ] **Step 2: Manual or Playwright browser walk-through**

Verify each of these in the browser at `http://localhost:5173/captures/new`:

1. Create / select template "Lô-Đề-Xiên-Test".
2. Upload `test_23.png` (or any small PNG).
3. Auto-redirect to `/captures/<id>`.
4. Image with bbox overlay renders (3 stub bboxes around 23, 5, 105).
5. Click a bbox → inline correction input appears, save with new value, bbox label updates.
6. In a group panel, click "Ghi âm" → grant mic permission → speak briefly → click "Đang ghi... (bấm để dừng)" → audio uploads → transcript + numbers appear → bboxes get colored per group.
7. Repeat for each group in the template.
8. Click "Finalize" → status changes to "final", `final_value` displayed.

- [ ] **Step 3: Stop servers + tag**

```bash
pkill -f "uvicorn app.main" 2>/dev/null; pkill -f vite 2>/dev/null
cd /Users/it/Documents/MySource/voiceApp
git tag plan-5-complete
git log --oneline | head -10
```

---

## Verification Checklist (end of Plan 5)

- [ ] `npm run build` clean.
- [ ] 8 frontend tests still pass.
- [ ] Backend serves `/media/captures/*.png` (added 2 new tests, total 154 backend).
- [ ] CaptureDetail page renders image + bbox overlay.
- [ ] Click bbox → inline editor → PATCH succeeds → bbox label updates.
- [ ] Audio recorder UI starts/stops and uploads.
- [ ] After audio upload, bboxes get colored per group, GroupPanel shows transcript + parsed numbers + sum + matches.
- [ ] Finalize button computes correct `final_value` and locks status.
- [ ] NewCapture redirects to detail page after upload.
- [ ] Tag `plan-5-complete` exists.

## What Plan 5 explicitly does NOT do (deferred)

- ❌ History page listing past captures (Plan 6)
- ❌ Capture metadata edit UI (writer_name, note_date, tags) (Plan 6)
- ❌ Manual match toggle UI (click 2 elements: OCR + audio_group → toggle) — defer; current auto-match + correction flow covers most cases
- ❌ Real PWA icons (Plan 6 polish)
- ❌ Lottery OCR + settlement (Plan 11)
- ❌ Risk analysis UI (Plan 8)
