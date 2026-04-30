import { useState } from 'react'
import { useTemplates, useCreateTemplate } from '../hooks/useTemplates'
import type { BetType, GroupDef } from '../api/types'

const BET_TYPES: BetType[] = ['lo', 'de', 'xien_2', 'xien_3', 'xien_4', '3cang', 'xien_quay']

export default function Templates() {
  const { data: templates, isLoading, error } = useTemplates()
  const createMutation = useCreateTemplate()
  const [name, setName] = useState('')
  const [groups, setGroups] = useState<GroupDef[]>([
    { index: 1, label: 'Lô', bet_type: 'lo', multiplier: 80, default_provinces: ['HN'] },
  ])

  const addGroup = () =>
    setGroups([...groups, {
      index: groups.length + 1,
      label: `Group ${groups.length + 1}`,
      bet_type: 'lo',
      multiplier: 80,
      default_provinces: ['HN'],
    }])

  const updateGroup = (i: number, patch: Partial<GroupDef>) => {
    setGroups(groups.map((g, idx) => (idx === i ? { ...g, ...patch } : g)))
  }

  const removeGroup = (i: number) => setGroups(groups.filter((_, idx) => idx !== i))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    await createMutation.mutateAsync({ name, groups })
    setName('')
    setGroups([{ index: 1, label: 'Lô', bet_type: 'lo', multiplier: 80, default_provinces: ['HN'] }])
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Templates</h1>

      <form onSubmit={submit} className="space-y-4 bg-slate-800 p-4 rounded">
        <h2 className="font-semibold">Tạo template mới</h2>
        <input
          className="w-full px-3 py-2 rounded bg-slate-700 text-white"
          placeholder="Tên template"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        {groups.map((g, i) => (
          <div key={i} className="flex flex-wrap gap-2 items-center bg-slate-900 p-2 rounded">
            <input
              className="px-2 py-1 rounded bg-slate-700 w-32"
              placeholder="Label"
              value={g.label}
              onChange={(e) => updateGroup(i, { label: e.target.value })}
            />
            <select
              className="px-2 py-1 rounded bg-slate-700"
              value={g.bet_type}
              onChange={(e) => updateGroup(i, { bet_type: e.target.value as BetType })}
            >
              {BET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input
              type="number"
              step="0.1"
              className="px-2 py-1 rounded bg-slate-700 w-24"
              placeholder="Multiplier"
              value={g.multiplier}
              onChange={(e) => updateGroup(i, { multiplier: parseFloat(e.target.value) || 0 })}
            />
            <input
              className="px-2 py-1 rounded bg-slate-700 w-32"
              placeholder="Provinces (comma)"
              value={(g.default_provinces ?? []).join(',')}
              onChange={(e) => updateGroup(i, {
                default_provinces: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
              })}
            />
            {groups.length > 1 && (
              <button type="button" onClick={() => removeGroup(i)} className="px-2 py-1 text-red-400">×</button>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <button type="button" onClick={addGroup} className="px-3 py-1 bg-slate-700 rounded">+ Group</button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-1 bg-sky-600 rounded disabled:opacity-50"
          >
            {createMutation.isPending ? 'Đang tạo...' : 'Tạo'}
          </button>
        </div>
        {createMutation.error && (
          <div className="text-red-400 text-sm">{(createMutation.error as Error).message}</div>
        )}
      </form>

      <div>
        <h2 className="font-semibold mb-2">Danh sách</h2>
        {isLoading && <div className="text-slate-400">Loading...</div>}
        {error && <div className="text-red-400">{(error as Error).message}</div>}
        {templates && templates.length === 0 && <div className="text-slate-400">Chưa có template nào.</div>}
        <ul className="space-y-2">
          {templates?.map((t) => (
            <li key={t.id} className="bg-slate-800 p-3 rounded">
              <div className="font-semibold">{t.name}</div>
              <div className="text-sm text-slate-400">
                {t.groups.map((g) => `${g.label}(${g.bet_type}×${g.multiplier})`).join(', ')}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
