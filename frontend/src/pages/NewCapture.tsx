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
