# Plan 4 — Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng PWA frontend (React + TypeScript + Vite + Tailwind + vite-plugin-pwa) với: API client typed matching backend, camera capture hook, audio recorder hook, 3 trang đầu tiên (Home, Templates, NewCapture). Cuối plan: chạy `npm run dev`, mở browser, tạo template + chụp ảnh + thấy OCR result hiển thị end-to-end với backend stub.

**Architecture:** Vite SPA, React Router, TanStack Query để fetch + cache, axios client. Tailwind utility-first cho UI nhanh. PWA manifest + service worker tự generate qua vite-plugin-pwa. Test bằng Vitest + Testing Library cho hooks + utility; UI components verify thủ công qua browser. Không Playwright trong plan này (defer).

**Tech Stack:** Node 20+, npm, Vite 5, React 18, TypeScript 5, TailwindCSS 3, axios, @tanstack/react-query 5, react-router-dom 6, vite-plugin-pwa, vitest, @testing-library/react.

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §3 (kiến trúc), §10 (frontend structure), §11 (tech stack frontend).

**Pre-flight:** Plan 3 complete (tag `plan-3-complete`), 152 tests passing, 40 commits. Backend ready at `http://localhost:8000` via `uvicorn app.main:app --port 8000`.

---

## File Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── vitest.config.ts
├── .gitignore
├── public/
│   ├── favicon.svg
│   └── icons/
│       ├── icon-192.png       # placeholder
│       └── icon-512.png       # placeholder
└── src/
    ├── main.tsx                          # React root + router + QueryClient + PWA register
    ├── App.tsx                           # Layout shell (nav + <Outlet />)
    ├── api/
    │   ├── client.ts                     # axios instance with baseURL from env
    │   └── types.ts                      # TS types mirroring backend Pydantic schemas
    ├── hooks/
    │   ├── useCamera.ts                  # getUserMedia (video), capture frame → Blob
    │   ├── useRecorder.ts                # MediaRecorder for audio → Blob
    │   ├── useProvinces.ts               # TanStack Query
    │   ├── useTemplates.ts               # TanStack Query (list + create)
    │   └── useCaptures.ts                # TanStack Query (list + create)
    ├── pages/
    │   ├── Home.tsx                      # Landing — links to other pages
    │   ├── Templates.tsx                 # List + create template form
    │   └── NewCapture.tsx                # Pick template → set group_provinces → camera → submit
    ├── components/
    │   ├── CameraCapture.tsx             # <video> + capture button → onCapture(Blob)
    │   ├── AudioRecorder.tsx             # mic button + waveform → onRecording(Blob)
    │   └── OcrOverlay.tsx                # canvas overlay (used in Plan 5; stub here)
    └── styles/
        └── globals.css                   # Tailwind imports
```

**Responsibilities:**
- `api/client.ts` — single axios instance, base URL from `VITE_API_BASE_URL` env, interceptors for error logging.
- `api/types.ts` — handwritten TS types mirroring backend schemas; not auto-generated to avoid build complexity.
- `hooks/useCamera.ts` — encapsulates getUserMedia lifecycle + frame capture. Returns `{ videoRef, capture, error }`.
- `hooks/useRecorder.ts` — wraps MediaRecorder. Returns `{ start, stop, isRecording, blob, error }`.
- `pages/NewCapture.tsx` — wizard flow: select template → camera capture → POST `/api/captures` → display OCR results.

---

## Task 1: Pre-flight — Node setup verify

**Files:** none

- [ ] **Step 1: Check Node + npm**

Run:
```bash
node --version
npm --version
```

Expected: Node 20.x or higher; npm 10.x.

If Node missing or older, ask user to install via `brew install node@20` (one-time auth).

- [ ] **Step 2: No commit — system check only**

---

## Task 2: Vite scaffold + base deps

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/.gitignore`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Create dir + package.json**

```bash
mkdir -p /Users/it/Documents/MySource/voiceApp/frontend/{src,public}
```

Create `/Users/it/Documents/MySource/voiceApp/frontend/package.json`:

```json
{
  "name": "voiceapp-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.16",
    "axios": "^1.7.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vite-plugin-pwa": "^0.20.5",
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20",
    "vitest": "^2.1.4",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.2",
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 2: Create `frontend/.gitignore`**

```
node_modules
dist
dist-ssr
*.local
.env
.env.*
!.env.example
.vscode
.idea
coverage
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta name="theme-color" content="#0f172a" />
    <title>VoiceApp</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'VoiceApp',
        short_name: 'VoiceApp',
        description: 'Handwritten number recognition with audio supervision',
        theme_color: '#0f172a',
        background_color: '#0f172a',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 5: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "types": ["vite/client", "vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 6: Create `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 7: Create minimal `src/App.tsx`**

```tsx
import { Outlet, Link } from 'react-router-dom'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="border-b border-slate-700 px-4 py-3 flex gap-4">
        <Link to="/" className="font-semibold">VoiceApp</Link>
        <Link to="/templates" className="text-slate-300 hover:text-white">Templates</Link>
        <Link to="/captures/new" className="text-slate-300 hover:text-white">New Capture</Link>
      </header>
      <main className="p-4 max-w-3xl mx-auto">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 8: Create minimal `src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

function Home() {
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-bold">VoiceApp</h1>
      <p className="text-slate-300">Bộ ghi âm + nhận diện số viết tay.</p>
    </div>
  )
}

function Placeholder({ name }: { name: string }) {
  return <div className="text-slate-300">{name} — TBD</div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<Home />} />
            <Route path="templates" element={<Placeholder name="Templates" />} />
            <Route path="captures/new" element={<Placeholder name="New Capture" />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 9: Create empty `src/styles/globals.css`** (Tailwind added in Task 3)

```css
/* placeholder — Tailwind directives added in Task 3 */
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
```

- [ ] **Step 10: Install + verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm install
```

Wait for install (1-3 min, ~250 packages).

Then:
```bash
npm run build
```

Expected: clean build, output in `dist/`.

If build fails, do NOT edit code to make it pass — report the error verbatim.

- [ ] **Step 11: Commit (excludes node_modules)**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/.gitignore frontend/package.json frontend/package-lock.json frontend/index.html frontend/vite.config.ts frontend/tsconfig.json frontend/tsconfig.node.json frontend/src/App.tsx frontend/src/main.tsx frontend/src/styles/globals.css
git commit -m "feat(frontend): scaffold Vite + React + TS + router + TanStack Query"
```

---

## Task 3: Tailwind + PWA placeholders

**Files:**
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Modify: `frontend/src/styles/globals.css`
- Create: `frontend/public/favicon.svg`
- Create: `frontend/public/icons/icon-192.png`
- Create: `frontend/public/icons/icon-512.png`

- [ ] **Step 1: Create `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 2: Create `frontend/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 3: Replace `frontend/src/styles/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

- [ ] **Step 4: Create `frontend/public/favicon.svg`**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
```

- [ ] **Step 5: Generate placeholder PNG icons via Node script (one-shot)**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
mkdir -p public/icons
node -e "
const fs = require('fs');
// 1×1 transparent PNG bytes
const px = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64');
fs.writeFileSync('public/icons/icon-192.png', px);
fs.writeFileSync('public/icons/icon-512.png', px);
console.log('placeholder icons written');
"
```

(Real icons can be added later — Plan 6 polish or whenever the user has artwork. PWA install will work but icon will be 1×1.)

- [ ] **Step 6: Verify build still passes**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

Expected: clean build; manifest.webmanifest + sw.js generated in `dist/`.

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/tailwind.config.js frontend/postcss.config.js frontend/src/styles/globals.css frontend/public/favicon.svg frontend/public/icons/icon-192.png frontend/public/icons/icon-512.png
git commit -m "feat(frontend): wire Tailwind + PWA placeholder icons"
```

---

## Task 4: API types + axios client + Vitest setup

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test-setup.ts`
- Create: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
```

- [ ] **Step 2: Create `frontend/src/test-setup.ts`**

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 3: Create `frontend/src/api/types.ts`**

```ts
// Mirrors backend Pydantic schemas in backend/app/schemas.py.
// Hand-maintained — keep in sync when backend schemas change.

export type BetType = 'lo' | 'de' | 'xien_2' | 'xien_3' | 'xien_4' | '3cang' | 'xien_quay'
export type CaptureStatus = 'draft' | 'final' | 'settled'
export type Region = 'mb' | 'mt' | 'mn'
export type MatchSource = 'auto' | 'manual'

export interface GroupDef {
  index: number
  label: string
  bet_type: BetType
  multiplier: number
  default_provinces?: string[]
}

export interface Template {
  id: number
  name: string
  groups: GroupDef[]
  created_at: string
}

export interface Province {
  code: string
  region: Region
  name: string
}

export interface BBox {
  x: number
  y: number
  w: number
  h: number
}

export interface OcrNumber {
  id: number
  bbox: BBox
  raw_text: string | null
  raw_value: number | null
  corrected_value: number | null
  confidence: number | null
}

export interface MatchRecord {
  id: number
  ocr_number_id: number
  audio_group_id: number
  confidence: number | null
  source: MatchSource
}

export interface AudioGroup {
  id: number
  capture_id: number
  group_index: number
  audio_path: string
  transcript: string | null
  parsed_numbers: number[] | null
  sum: number | null
  multiplier_snapshot: number
  matches: MatchRecord[]
}

export interface Capture {
  id: number
  template_id: number
  image_path: string
  status: CaptureStatus
  final_value: number | null
  group_provinces: Record<string, string[]>
  writer_name: string | null
  note_date: string | null
  tags: string[] | null
  notes: string | null
  ocr_numbers: OcrNumber[]
  audio_groups: AudioGroup[]
  created_at: string
  updated_at: string
}
```

- [ ] **Step 4: Create `frontend/src/api/client.ts`**

```ts
import axios from 'axios'
import type { Template, Capture, Province, GroupDef, AudioGroup, OcrNumber, MatchRecord } from './types'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export const api = axios.create({
  baseURL,
  headers: { Accept: 'application/json' },
})

// --- Provinces ---
export async function listProvinces(region?: 'mb' | 'mt' | 'mn'): Promise<Province[]> {
  const r = await api.get<Province[]>('/provinces', { params: region ? { region } : {} })
  return r.data
}

// --- Templates ---
export async function listTemplates(): Promise<Template[]> {
  const r = await api.get<Template[]>('/templates')
  return r.data
}

export async function createTemplate(body: { name: string; groups: GroupDef[] }): Promise<Template> {
  const r = await api.post<Template>('/templates', body)
  return r.data
}

export async function getTemplate(id: number): Promise<Template> {
  const r = await api.get<Template>(`/templates/${id}`)
  return r.data
}

// --- Captures ---
export interface CreateCaptureInput {
  template_id: number
  group_provinces: Record<number, string[]>
  image: Blob
  writer_name?: string
  note_date?: string
}

export async function createCapture(input: CreateCaptureInput): Promise<Capture> {
  const fd = new FormData()
  fd.append('template_id', String(input.template_id))
  fd.append('group_provinces', JSON.stringify(input.group_provinces))
  if (input.writer_name) fd.append('writer_name', input.writer_name)
  if (input.note_date) fd.append('note_date', input.note_date)
  fd.append('image', input.image, 'capture.png')
  const r = await api.post<Capture>('/captures', fd)
  return r.data
}

export async function listCaptures(): Promise<Capture[]> {
  const r = await api.get<Capture[]>('/captures')
  return r.data
}

export async function getCapture(id: number): Promise<Capture> {
  const r = await api.get<Capture>(`/captures/${id}`)
  return r.data
}

export async function patchOcr(captureId: number, ocrId: number, correctedValue: number | null): Promise<OcrNumber> {
  const r = await api.patch<OcrNumber>(`/captures/${captureId}/ocr/${ocrId}`, { corrected_value: correctedValue })
  return r.data
}

export async function uploadAudio(captureId: number, groupIndex: number, audio: Blob): Promise<AudioGroup> {
  const fd = new FormData()
  fd.append('group_index', String(groupIndex))
  fd.append('audio', audio, 'recording.webm')
  const r = await api.post<AudioGroup>(`/captures/${captureId}/audio`, fd)
  return r.data
}

export async function toggleMatch(captureId: number, body: {
  ocr_number_id: number
  audio_group_id: number
  action: 'add' | 'remove'
}): Promise<MatchRecord> {
  const r = await api.post<MatchRecord>(`/captures/${captureId}/matches`, body)
  return r.data
}

export async function finalizeCapture(captureId: number): Promise<Capture> {
  const r = await api.post<Capture>(`/captures/${captureId}/finalize`)
  return r.data
}
```

- [ ] **Step 5: Create test for client (verifies type-safe construction; no real network)**

Create `/Users/it/Documents/MySource/voiceApp/frontend/src/api/client.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { api, listProvinces } from './client'

describe('api client', () => {
  it('exposes axios instance with baseURL set', () => {
    expect(api.defaults.baseURL).toBeTruthy()
    expect(typeof api.get).toBe('function')
  })

  it('listProvinces is a function', () => {
    expect(typeof listProvinces).toBe('function')
  })
})
```

- [ ] **Step 6: Run vitest**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm test
```

Expected: 2 PASS.

- [ ] **Step 7: Verify build still passes**

```bash
npm run build
```

- [ ] **Step 8: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/vitest.config.ts frontend/src/test-setup.ts frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "feat(frontend): typed axios client + Vitest setup"
```

---

## Task 5: useCamera + useRecorder hooks

**Files:**
- Create: `frontend/src/hooks/useCamera.ts`
- Create: `frontend/src/hooks/useRecorder.ts`
- Create: `frontend/src/hooks/useCamera.test.ts`
- Create: `frontend/src/hooks/useRecorder.test.ts`

These hooks wrap browser APIs. Tests mock `navigator.mediaDevices` since jsdom doesn't have real media APIs.

- [ ] **Step 1: Create `frontend/src/hooks/useCamera.ts`**

```ts
import { useCallback, useEffect, useRef, useState } from 'react'

export interface UseCameraResult {
  videoRef: React.RefObject<HTMLVideoElement>
  start: () => Promise<void>
  stop: () => void
  capture: () => Promise<Blob | null>
  isActive: boolean
  error: string | null
}

export function useCamera(): UseCameraResult {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setIsActive(false)
  }, [])

  const start = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setIsActive(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const capture = useCallback(async (): Promise<Blob | null> => {
    const v = videoRef.current
    if (!v || !streamRef.current) return null
    const w = v.videoWidth
    const h = v.videoHeight
    if (!w || !h) return null
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(v, 0, 0, w, h)
    return await new Promise((resolve) => canvas.toBlob((b) => resolve(b), 'image/png', 0.92))
  }, [])

  // cleanup on unmount
  useEffect(() => stop, [stop])

  return { videoRef, start, stop, capture, isActive, error }
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useRecorder.ts`**

```ts
import { useCallback, useRef, useState } from 'react'

export interface UseRecorderResult {
  start: () => Promise<void>
  stop: () => void
  isRecording: boolean
  blob: Blob | null
  error: string | null
  reset: () => void
}

export function useRecorder(mimeType = 'audio/webm'): UseRecorderResult {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(() => {
    setBlob(null)
    chunksRef.current = []
  }, [])

  const start = useCallback(async () => {
    setError(null)
    setBlob(null)
    chunksRef.current = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream, MediaRecorder.isTypeSupported(mimeType) ? { mimeType } : undefined)
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const out = new Blob(chunksRef.current, { type: mimeType })
        setBlob(out)
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      recorder.start()
      recorderRef.current = recorder
      setIsRecording(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [mimeType])

  const stop = useCallback(() => {
    const r = recorderRef.current
    if (r && r.state !== 'inactive') {
      r.stop()
    }
    setIsRecording(false)
  }, [])

  return { start, stop, isRecording, blob, error, reset }
}
```

- [ ] **Step 3: Create `frontend/src/hooks/useCamera.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCamera } from './useCamera'

describe('useCamera', () => {
  let getUserMediaMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    getUserMediaMock = vi.fn()
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: { getUserMedia: getUserMediaMock },
      configurable: true,
    })
  })

  it('starts inactive', () => {
    const { result } = renderHook(() => useCamera())
    expect(result.current.isActive).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('reports error when getUserMedia rejects', async () => {
    getUserMediaMock.mockRejectedValue(new Error('Permission denied'))
    const { result } = renderHook(() => useCamera())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.error).toBe('Permission denied')
    expect(result.current.isActive).toBe(false)
  })

  it('returns null capture if not started', async () => {
    const { result } = renderHook(() => useCamera())
    const blob = await result.current.capture()
    expect(blob).toBeNull()
  })
})
```

- [ ] **Step 4: Create `frontend/src/hooks/useRecorder.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRecorder } from './useRecorder'

describe('useRecorder', () => {
  let getUserMediaMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    getUserMediaMock = vi.fn()
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: { getUserMedia: getUserMediaMock },
      configurable: true,
    })
    // jsdom lacks MediaRecorder — provide a minimal mock
    class FakeRecorder {
      state = 'recording'
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      static isTypeSupported() { return true }
      start() {}
      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['x']) })
        this.onstop?.()
      }
    }
    ;(global as unknown as { MediaRecorder: unknown }).MediaRecorder = FakeRecorder
  })

  it('starts inactive with no blob', () => {
    const { result } = renderHook(() => useRecorder())
    expect(result.current.isRecording).toBe(false)
    expect(result.current.blob).toBeNull()
  })

  it('reports error when getUserMedia rejects', async () => {
    getUserMediaMock.mockRejectedValue(new Error('mic denied'))
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.error).toBe('mic denied')
  })

  it('produces a blob after stop()', async () => {
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: () => {} }] })
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.isRecording).toBe(true)
    act(() => {
      result.current.stop()
    })
    expect(result.current.blob).not.toBeNull()
    expect(result.current.blob?.size).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 5: Run vitest**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm test
```

Expected: 2 (api) + 3 (camera) + 3 (recorder) = 8 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/hooks/
git commit -m "feat(frontend): useCamera + useRecorder hooks with mocked-API tests"
```

---

## Task 6: Templates page (list + create)

**Files:**
- Create: `frontend/src/hooks/useTemplates.ts`
- Create: `frontend/src/pages/Templates.tsx`
- Modify: `frontend/src/main.tsx` (replace placeholder route)

- [ ] **Step 1: Create `frontend/src/hooks/useTemplates.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listTemplates, createTemplate } from '../api/client'
import type { GroupDef } from '../api/types'

export function useTemplates() {
  return useQuery({ queryKey: ['templates'], queryFn: listTemplates })
}

export function useCreateTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; groups: GroupDef[] }) => createTemplate(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['templates'] })
    },
  })
}
```

- [ ] **Step 2: Create `frontend/src/pages/Templates.tsx`**

```tsx
import { useState } from 'react'
import { useTemplates, useCreateTemplate } from '../hooks/useTemplates'
import type { BetType, GroupDef } from '../api/types'

const BET_TYPES: BetType[] = ['lo', 'de', 'xien_2', 'xien_3', 'xien_4', '3cang', 'xien_quay']

export default function Templates() {
  const { data: templates, isLoading, error } = useTemplates()
  const createMutation = useCreateTemplate()
  const [name, setName] = useState('')
  const [groups, setGroups] = useState<GroupDef[]>([
    { index: 1, label: 'Lô', bet_type: 'lo', multiplier: 80, default_provinces: ['HN'] },
  ])

  const addGroup = () =>
    setGroups([...groups, {
      index: groups.length + 1,
      label: `Group ${groups.length + 1}`,
      bet_type: 'lo',
      multiplier: 80,
      default_provinces: ['HN'],
    }])

  const updateGroup = (i: number, patch: Partial<GroupDef>) => {
    setGroups(groups.map((g, idx) => (idx === i ? { ...g, ...patch } : g)))
  }

  const removeGroup = (i: number) => setGroups(groups.filter((_, idx) => idx !== i))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    await createMutation.mutateAsync({ name, groups })
    setName('')
    setGroups([{ index: 1, label: 'Lô', bet_type: 'lo', multiplier: 80, default_provinces: ['HN'] }])
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Templates</h1>

      <form onSubmit={submit} className="space-y-4 bg-slate-800 p-4 rounded">
        <h2 className="font-semibold">Tạo template mới</h2>
        <input
          className="w-full px-3 py-2 rounded bg-slate-700 text-white"
          placeholder="Tên template"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        {groups.map((g, i) => (
          <div key={i} className="flex flex-wrap gap-2 items-center bg-slate-900 p-2 rounded">
            <input
              className="px-2 py-1 rounded bg-slate-700 w-32"
              placeholder="Label"
              value={g.label}
              onChange={(e) => updateGroup(i, { label: e.target.value })}
            />
            <select
              className="px-2 py-1 rounded bg-slate-700"
              value={g.bet_type}
              onChange={(e) => updateGroup(i, { bet_type: e.target.value as BetType })}
            >
              {BET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input
              type="number"
              step="0.1"
              className="px-2 py-1 rounded bg-slate-700 w-24"
              placeholder="Multiplier"
              value={g.multiplier}
              onChange={(e) => updateGroup(i, { multiplier: parseFloat(e.target.value) || 0 })}
            />
            <input
              className="px-2 py-1 rounded bg-slate-700 w-32"
              placeholder="Provinces (comma)"
              value={(g.default_provinces ?? []).join(',')}
              onChange={(e) => updateGroup(i, {
                default_provinces: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
              })}
            />
            {groups.length > 1 && (
              <button type="button" onClick={() => removeGroup(i)} className="px-2 py-1 text-red-400">×</button>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <button type="button" onClick={addGroup} className="px-3 py-1 bg-slate-700 rounded">+ Group</button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-1 bg-sky-600 rounded disabled:opacity-50"
          >
            {createMutation.isPending ? 'Đang tạo...' : 'Tạo'}
          </button>
        </div>
        {createMutation.error && (
          <div className="text-red-400 text-sm">{(createMutation.error as Error).message}</div>
        )}
      </form>

      <div>
        <h2 className="font-semibold mb-2">Danh sách</h2>
        {isLoading && <div className="text-slate-400">Loading...</div>}
        {error && <div className="text-red-400">{(error as Error).message}</div>}
        {templates && templates.length === 0 && <div className="text-slate-400">Chưa có template nào.</div>}
        <ul className="space-y-2">
          {templates?.map((t) => (
            <li key={t.id} className="bg-slate-800 p-3 rounded">
              <div className="font-semibold">{t.name}</div>
              <div className="text-sm text-slate-400">
                {t.groups.map((g) => `${g.label}(${g.bet_type}×${g.multiplier})`).join(', ')}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
```

- [ ] **Step 2b: Update `frontend/src/main.tsx`** — replace `Placeholder name="Templates"` route element with `<Templates />`. Add import:

Open `/Users/it/Documents/MySource/voiceApp/frontend/src/main.tsx`. Add at the top of imports:

```tsx
import Templates from './pages/Templates'
```

Then change the line:

```tsx
<Route path="templates" element={<Placeholder name="Templates" />} />
```

to:

```tsx
<Route path="templates" element={<Templates />} />
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

Expected: clean build.

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/hooks/useTemplates.ts frontend/src/pages/Templates.tsx frontend/src/main.tsx
git commit -m "feat(frontend): Templates page with create form + list"
```

---

## Task 7: Camera component + NewCapture page

**Files:**
- Create: `frontend/src/components/CameraCapture.tsx`
- Create: `frontend/src/hooks/useCaptures.ts`
- Create: `frontend/src/pages/NewCapture.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/src/components/CameraCapture.tsx`**

```tsx
import { useCamera } from '../hooks/useCamera'
import { useState } from 'react'

interface Props {
  onCapture: (blob: Blob) => void
}

export default function CameraCapture({ onCapture }: Props) {
  const { videoRef, start, stop, capture, isActive, error } = useCamera()
  const [busy, setBusy] = useState(false)

  const handleCapture = async () => {
    setBusy(true)
    try {
      const blob = await capture()
      if (blob) onCapture(blob)
    } finally {
      setBusy(false)
    }
  }

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) onCapture(f)
  }

  return (
    <div className="space-y-3">
      <video ref={videoRef} className="w-full max-w-md rounded bg-black" muted playsInline />
      <div className="flex flex-wrap gap-2">
        {!isActive && <button onClick={start} className="px-3 py-2 bg-sky-600 rounded">Bật camera</button>}
        {isActive && <button onClick={stop} className="px-3 py-2 bg-slate-700 rounded">Tắt</button>}
        {isActive && (
          <button onClick={handleCapture} disabled={busy} className="px-3 py-2 bg-emerald-600 rounded disabled:opacity-50">
            {busy ? 'Đang chụp...' : 'Chụp'}
          </button>
        )}
        <label className="px-3 py-2 bg-slate-700 rounded cursor-pointer">
          Hoặc upload file
          <input type="file" accept="image/*" className="hidden" onChange={onFile} />
        </label>
      </div>
      {error && <div className="text-red-400 text-sm">{error}</div>}
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useCaptures.ts`**

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createCapture, type CreateCaptureInput } from '../api/client'

export function useCreateCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateCaptureInput) => createCapture(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['captures'] }),
  })
}
```

- [ ] **Step 3: Create `frontend/src/pages/NewCapture.tsx`**

```tsx
import { useState } from 'react'
import { useTemplates } from '../hooks/useTemplates'
import { useCreateCapture } from '../hooks/useCaptures'
import CameraCapture from '../components/CameraCapture'
import type { Capture } from '../api/types'

export default function NewCapture() {
  const { data: templates, isLoading } = useTemplates()
  const createMutation = useCreateCapture()
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [groupProvinces, setGroupProvinces] = useState<Record<number, string[]>>({})
  const [result, setResult] = useState<Capture | null>(null)

  const selectedTemplate = templates?.find((t) => t.id === templateId)

  const onPickTemplate = (id: number) => {
    const t = templates?.find((x) => x.id === id)
    setTemplateId(id)
    if (t) {
      const initial: Record<number, string[]> = {}
      t.groups.forEach((g) => {
        initial[g.index] = g.default_provinces && g.default_provinces.length > 0 ? g.default_provinces : ['HN']
      })
      setGroupProvinces(initial)
    }
  }

  const updateGroupProvinces = (groupIndex: number, value: string) => {
    setGroupProvinces({
      ...groupProvinces,
      [groupIndex]: value.split(',').map((s) => s.trim()).filter(Boolean),
    })
  }

  const onCapture = async (blob: Blob) => {
    if (!templateId) return
    const cap = await createMutation.mutateAsync({
      template_id: templateId,
      group_provinces: groupProvinces,
      image: blob,
    })
    setResult(cap)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Capture mới</h1>

      <section className="space-y-2">
        <h2 className="font-semibold">1. Chọn template</h2>
        {isLoading && <div className="text-slate-400">Loading...</div>}
        <select
          className="px-3 py-2 rounded bg-slate-700 text-white"
          value={templateId ?? ''}
          onChange={(e) => onPickTemplate(parseInt(e.target.value))}
        >
          <option value="">-- chọn --</option>
          {templates?.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </section>

      {selectedTemplate && (
        <section className="space-y-2">
          <h2 className="font-semibold">2. Đài cho từng group</h2>
          {selectedTemplate.groups.map((g) => (
            <div key={g.index} className="flex gap-2 items-center">
              <span className="w-32 text-sm">{g.label} (×{g.multiplier}):</span>
              <input
                className="px-2 py-1 rounded bg-slate-700 text-white"
                value={(groupProvinces[g.index] ?? []).join(',')}
                onChange={(e) => updateGroupProvinces(g.index, e.target.value)}
                placeholder="HN,DNG,..."
              />
            </div>
          ))}
        </section>
      )}

      {selectedTemplate && (
        <section className="space-y-2">
          <h2 className="font-semibold">3. Chụp ảnh</h2>
          <CameraCapture onCapture={onCapture} />
          {createMutation.isPending && <div className="text-slate-400">Đang upload + OCR...</div>}
          {createMutation.error && <div className="text-red-400">{(createMutation.error as Error).message}</div>}
        </section>
      )}

      {result && (
        <section className="space-y-2">
          <h2 className="font-semibold">4. Kết quả OCR</h2>
          <div className="bg-slate-800 p-3 rounded">
            <div className="text-sm text-slate-400">Capture id: {result.id} (status: {result.status})</div>
            <ul className="mt-2 space-y-1">
              {result.ocr_numbers.map((n) => (
                <li key={n.id}>
                  <span className="font-mono">{n.raw_value ?? n.raw_text}</span>
                  <span className="text-slate-400 text-xs ml-2">conf={n.confidence?.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Update `frontend/src/main.tsx`**

Add import:

```tsx
import NewCapture from './pages/NewCapture'
```

Replace:

```tsx
<Route path="captures/new" element={<Placeholder name="New Capture" />} />
```

with:

```tsx
<Route path="captures/new" element={<NewCapture />} />
```

- [ ] **Step 5: Verify build**

```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run build
```

- [ ] **Step 6: Run tests (no new tests; existing 8 should still pass)**

```bash
npm test
```

Expected: 8 PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add frontend/src/components/CameraCapture.tsx frontend/src/hooks/useCaptures.ts frontend/src/pages/NewCapture.tsx frontend/src/main.tsx
git commit -m "feat(frontend): NewCapture page with camera + template select + OCR result display"
```

---

## Task 8: Manual end-to-end browser verification

**Files:** none (manual verification)

- [ ] **Step 1: Start backend**

In one terminal:
```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

Wait for "Application startup complete".

- [ ] **Step 2: Start frontend dev server**

In a SEPARATE terminal:
```bash
cd /Users/it/Documents/MySource/voiceApp/frontend
npm run dev
```

Wait for "Local: http://localhost:5173/".

- [ ] **Step 3: Manual browser test**

Open `http://localhost:5173/` in a Chromium-based browser:

1. Verify Home page renders with nav links.
2. Click "Templates" → form appears + empty list.
3. Fill: name="Smoke", keep default group → click "Tạo". Template appears in list.
4. Click "New Capture" → select "Smoke" from dropdown → group provinces input shows "HN".
5. Click "Bật camera" → grant permission → see live video.
6. Click "Chụp" → after 1-2s, "Kết quả OCR" section appears with 3 stub numbers (23, 5, 105).
7. Open browser DevTools → Application → Manifest: verify VoiceApp manifest loaded; Service Worker registered.

If any step fails, debug and report.

- [ ] **Step 4: Take a screenshot of working OCR result for record (optional)**

Save as `docs/superpowers/screenshots/plan-4-newcapture.png` (or skip).

- [ ] **Step 5: Stop both dev servers (Ctrl+C in each terminal)**

- [ ] **Step 6: Tag plan completion**

```bash
cd /Users/it/Documents/MySource/voiceApp
git tag plan-4-complete
git log --oneline | head -10
```

Expected: tag `plan-4-complete` exists. ~46-48 commits total.

---

## Verification Checklist (end of Plan 4)

- [ ] `cd frontend && npm install && npm run build` — clean build.
- [ ] `npm test` — 8 PASS (api: 2, useCamera: 3, useRecorder: 3).
- [ ] `npm run dev` — Vite dev server boots, HMR works.
- [ ] PWA manifest + service worker generated in `dist/`.
- [ ] Browser can: see Home, create + list templates, select template, grant camera, capture image, see OCR result from backend.
- [ ] Backend at `localhost:8000` is reached via Vite proxy `/api/*`.
- [ ] Tag `plan-4-complete` exists.

## What Plan 4 explicitly does NOT do (deferred)

- ❌ OCR overlay drawing on image (Plan 5)
- ❌ OCR correction UI (tick + edit) (Plan 5)
- ❌ Audio recorder UI integration with capture flow (Plan 5)
- ❌ Match visualization / manual match toggling UI (Plan 5)
- ❌ Finalize button + result display (Plan 5)
- ❌ History page (Plan 6)
- ❌ Capture detail page (Plan 5/6)
- ❌ Real high-res PWA icons (Plan 6 polish)
- ❌ Playwright E2E (defer)
