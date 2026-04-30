import axios from 'axios'
import type { Template, Capture, Province, GroupDef, AudioGroup, OcrNumber, MatchRecord } from './types'

function backendOrigin(): string {
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (!envBase || envBase.startsWith('/')) {
    // proxied through vite — same origin
    return ''
  }
  // strip trailing /api if present
  return envBase.replace(/\/api\/?$/, '')
}

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
