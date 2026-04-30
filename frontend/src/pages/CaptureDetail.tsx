import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useCapture, usePatchOcr, useUploadAudio } from '../hooks/useCapture'
import { useTemplates } from '../hooks/useTemplates'
import OcrOverlay from '../components/OcrOverlay'
import OcrCorrectionInput from '../components/OcrCorrectionInput'
import GroupPanel from '../components/GroupPanel'
import { getImageURL } from '../api/client'

export default function CaptureDetail() {
  const { id } = useParams<{ id: string }>()
  const captureId = id ? parseInt(id) : null
  const { data: capture, isLoading, error } = useCapture(captureId)
  const [editingOcrId, setEditingOcrId] = useState<number | null>(null)
  const patchMutation = usePatchOcr(captureId ?? 0)
  const uploadAudio = useUploadAudio(captureId ?? 0)
  const { data: templates } = useTemplates()
  const template = templates?.find((t) => t.id === capture?.template_id)

  if (isLoading) return <div className="text-slate-300">Loading...</div>
  if (error) return <div className="text-red-400">{(error as Error).message}</div>
  if (!capture) return <div className="text-slate-400">Not found</div>

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

      <div className="grid lg:grid-cols-2 gap-4">
        <div>
          <OcrOverlay
            imageUrl={getImageURL(capture.image_path)}
            ocrNumbers={capture.ocr_numbers}
            colorByOcrId={colorByOcrId}
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
        </div>
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
      </div>
    </div>
  )
}
