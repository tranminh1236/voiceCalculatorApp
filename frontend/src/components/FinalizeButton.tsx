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
