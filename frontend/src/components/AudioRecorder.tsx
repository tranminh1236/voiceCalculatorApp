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
