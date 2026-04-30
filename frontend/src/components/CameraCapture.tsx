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
