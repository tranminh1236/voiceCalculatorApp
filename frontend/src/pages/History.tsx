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
