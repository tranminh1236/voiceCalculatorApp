interface Props {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
  isPending?: boolean
}

export default function ConfirmModal({
  title,
  message,
  confirmLabel = 'OK',
  cancelLabel = 'Hủy',
  destructive,
  onConfirm,
  onCancel,
  isPending,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-800 rounded p-5 max-w-md w-full space-y-3">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-slate-300 text-sm">{message}</p>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-3 py-2 bg-slate-700 rounded disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className={`px-3 py-2 rounded disabled:opacity-50 ${destructive ? 'bg-red-600' : 'bg-sky-600'}`}
          >
            {isPending ? '...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
