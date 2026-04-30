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
