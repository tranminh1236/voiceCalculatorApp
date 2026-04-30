import { useParams } from 'react-router-dom'
import { useCapture } from '../hooks/useCapture'
import OcrOverlay from '../components/OcrOverlay'
import { getImageURL } from '../api/client'

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
    </div>
  )
}
