import { useState } from 'react'
import { useCaptureRisk } from '../hooks/useCapture'

interface Props {
  captureId: number
}

const PRESETS = [0, 100_000, 500_000, 1_000_000]

export default function RiskPanel({ captureId }: Props) {
  const [threshold, setThreshold] = useState(0)
  const { data: report, isLoading, error } = useCaptureRisk(captureId, threshold)

  return (
    <div className="bg-slate-800 p-3 rounded space-y-3">
      <div className="flex justify-between items-baseline flex-wrap gap-2">
        <h3 className="font-semibold">Risk analysis</h3>
        {report && (
          <span className="text-sm text-slate-400">
            Vốn: <strong className="text-slate-200">{report.total_capital.toLocaleString()}</strong>
            {' · '}
            <span className="text-emerald-400">{report.take_count} take</span>
            {' / '}
            <span className="text-rose-400">{report.pass_count} pass</span>
          </span>
        )}
      </div>

      <div className="flex gap-2 items-center flex-wrap">
        <label className="text-sm text-slate-400">Ngưỡng lãi tối thiểu:</label>
        <input
          type="number"
          step="1000"
          className="px-2 py-1 rounded bg-slate-700 text-white w-32"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
        />
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setThreshold(p)}
            className={`px-2 py-1 text-xs rounded ${threshold === p ? 'bg-sky-600' : 'bg-slate-700'}`}
          >
            {p === 0 ? 'hòa vốn' : p.toLocaleString()}
          </button>
        ))}
      </div>

      {isLoading && <div className="text-slate-400 text-sm">Đang tính...</div>}
      {error && <div className="text-red-400 text-sm">{(error as Error).message}</div>}

      {report && report.entries.length === 0 && (
        <div className="text-slate-400 text-sm">Chưa có audio group nào — chưa tính được risk.</div>
      )}

      {report && report.entries.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs">
              <tr>
                <th className="text-left py-1">Group</th>
                <th className="text-right py-1">Stake</th>
                <th className="text-right py-1">×Đài</th>
                <th className="text-right py-1">Eff.</th>
                <th className="text-right py-1">×Mult</th>
                <th className="text-right py-1">Payout</th>
                <th className="text-right py-1">Net nếu trúng</th>
                <th className="text-right py-1">% vốn</th>
                <th className="text-center py-1">Khuyến nghị</th>
              </tr>
            </thead>
            <tbody>
              {report.entries.map((e, i) => (
                <tr key={i} className="border-t border-slate-700">
                  <td className="py-1">G{e.group_index}</td>
                  <td className="text-right py-1">{e.stake.toLocaleString()}</td>
                  <td className="text-right py-1">{e.num_provinces}</td>
                  <td className="text-right py-1">{e.effective_stake.toLocaleString()}</td>
                  <td className="text-right py-1">×{e.multiplier}</td>
                  <td className="text-right py-1">{e.payout_if_hits.toLocaleString()}</td>
                  <td className={
                    'text-right py-1 ' +
                    (e.net_if_hits >= 0 ? 'text-emerald-400' : 'text-rose-400')
                  }>
                    {e.net_if_hits >= 0 ? '+' : ''}{e.net_if_hits.toLocaleString()}
                  </td>
                  <td className="text-right py-1">{(e.capital_share * 100).toFixed(1)}%</td>
                  <td className="text-center py-1">
                    <span className={
                      'px-2 py-0.5 rounded text-xs ' +
                      (e.recommendation === 'take' ? 'bg-emerald-900 text-emerald-300' : 'bg-rose-900 text-rose-300')
                    }>
                      {e.recommendation.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
