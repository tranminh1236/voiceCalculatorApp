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
