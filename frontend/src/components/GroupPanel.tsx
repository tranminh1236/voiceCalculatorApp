import AudioRecorder from './AudioRecorder'
import type { AudioGroup, GroupDef, OcrNumber } from '../api/types'

interface Props {
  groupDef: GroupDef
  audioGroups: AudioGroup[]  // recordings already made for this group_index (can be 0+)
  ocrNumbers: OcrNumber[]    // for resolving match → value
  onRecord: (audio: Blob) => void
  uploading?: boolean
}

export default function GroupPanel({ groupDef, audioGroups, ocrNumbers, onRecord, uploading }: Props) {
  const ocrById = new Map(ocrNumbers.map((n) => [n.id, n]))

  return (
    <div className="bg-slate-800 p-3 rounded space-y-3">
      <div className="flex justify-between items-baseline">
        <h3 className="font-semibold">
          {groupDef.label}
          <span className="text-xs text-slate-400 ml-2">
            ({groupDef.bet_type} × {groupDef.multiplier})
          </span>
        </h3>
        <div className="text-xs text-slate-400">
          {audioGroups.length} bản ghi
        </div>
      </div>

      <AudioRecorder onComplete={onRecord} busy={uploading} />

      {audioGroups.map((g) => (
        <div key={g.id} className="border-t border-slate-700 pt-2 text-sm space-y-1">
          {g.transcript && (
            <div className="text-slate-300">
              <span className="text-slate-500">Transcript:</span> {g.transcript}
            </div>
          )}
          {g.parsed_numbers && (
            <div className="text-slate-300">
              <span className="text-slate-500">Numbers:</span>{' '}
              {g.parsed_numbers.join(' + ')} ={' '}
              <strong>{g.sum?.toLocaleString() ?? '—'}</strong>
            </div>
          )}
          <div className="text-xs text-slate-400">
            {g.matches.length} match{g.matches.length !== 1 ? 'es' : ''}:{' '}
            {g.matches.map((m) => {
              const n = ocrById.get(m.ocr_number_id)
              const val = n ? (n.corrected_value ?? n.raw_value) : '?'
              return `${val}(${m.source[0]})`
            }).join(', ')}
          </div>
        </div>
      ))}
    </div>
  )
}
