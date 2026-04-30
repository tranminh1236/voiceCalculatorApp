import { useEffect, useRef, useState } from 'react'

interface Props {
  initialValue: number | null
  onSave: (value: number | null) => void
  onCancel: () => void
  isPending?: boolean
}

export default function OcrCorrectionInput({ initialValue, onSave, onCancel, isPending }: Props) {
  const [value, setValue] = useState<string>(initialValue === null ? '' : String(initialValue))
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed === '') {
      onSave(null)
      return
    }
    const num = Number(trimmed)
    if (Number.isFinite(num)) {
      onSave(num)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-center bg-slate-800 p-2 rounded">
      <input
        ref={inputRef}
        type="number"
        step="any"
        className="px-2 py-1 rounded bg-slate-700 text-white w-32"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isPending}
      />
      <button type="submit" disabled={isPending} className="px-3 py-1 bg-emerald-600 rounded disabled:opacity-50">
        Lưu
      </button>
      <button type="button" onClick={onCancel} disabled={isPending} className="px-3 py-1 bg-slate-700 rounded">
        Hủy
      </button>
      <button
        type="button"
        onClick={() => onSave(null)}
        disabled={isPending}
        className="px-3 py-1 text-slate-400 hover:text-red-400"
        title="Xóa correction (về raw value)"
      >
        Xóa
      </button>
    </form>
  )
}
