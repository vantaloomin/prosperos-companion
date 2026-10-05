import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { LifeSettings as Limits } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextInput, Toggle } from '../../components/Fields'

const KEY = ['life-settings']
type NumberKey = 'catch_up_max_events' | 'catch_up_lookback_hours' | 'return_gap_hours' | 'background_interval_minutes' | 'background_daily_events'

const LIMITS: { key: NumberKey; label: string; min: number; max: number; hint: string }[] = [
  { key: 'catch_up_max_events', label: 'Most events when you return', min: 0, max: 6, hint: 'However long you were away.' },
  { key: 'catch_up_lookback_hours', label: 'How far back to fill in (hours)', min: 6, max: 336, hint: 'Older time away stays quiet.' },
  { key: 'return_gap_hours', label: 'Time away before catching up (hours)', min: 1, max: 48, hint: '' },
  { key: 'background_interval_minutes', label: 'Minutes between background updates', min: 15, max: 1440, hint: '' },
  { key: 'background_daily_events', label: 'Most background events a day', min: 0, max: 8, hint: '' },
]

export function LifeSettings({ name }: { name: string }) {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: KEY, queryFn: () => api<Limits>('/life/settings') })
  const [pending, setPending] = useState<Partial<Limits>>({})
  const [draft, setDraft] = useState<Partial<Record<NumberKey, string>>>({})
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const save = async (change: Partial<Limits>, done?: string) => {
    setPending((current) => ({ ...current, ...change }))
    try {
      const saved = await api<Limits>('/life/settings', change, 'PUT')
      setPending(saved)
      client.setQueryData(KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
      setResult(done ? { tone: 'info', text: done } : null)
      return true
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
      setPending({})
      return false
    }
  }
  if (!settings.data) return null
  const data = { ...settings.data, ...pending }
  const changed = Object.entries(draft).filter(([key, value]) => value !== undefined && Number(value) !== data[key as NumberKey])
  const saveLimits = async () => {
    if (await save(Object.fromEntries(changed.map(([key, value]) => [key, Number(value)])), 'Limits saved.')) setDraft({})
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="life-heading">
      <div>
        <h2 id="life-heading">{name}'s life</h2>
        <p className="subtle">When you come back, a few things that fit {name}'s routine are written for the time you were away. Nothing is written for time while paused.</p>
      </div>
      <Toggle label="Catch up when you return" checked={data.catch_up_on_return} onChange={(value) => void save({ catch_up_on_return: value })} />
      <Toggle label="Add everyday events without asking" checked={data.automatic_events} onChange={(value) => void save({ automatic_events: value })}
        hint="Off: new events wait in Today for you to keep or discard. Big changes to who they are or your relationship always wait for you." />
      <div className="form-grid">
        {LIMITS.map((limit) => (
          <TextInput key={limit.key} label={limit.label} type="number" value={draft[limit.key] ?? String(data[limit.key])} hint={limit.hint || `${limit.min} to ${limit.max}.`}
            onChange={(value) => setDraft((current) => ({ ...current, [limit.key]: value }))} />
        ))}
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      {changed.length > 0 && <div className="form-actions"><button type="button" className="button primary" onClick={() => void saveLimits()}>Save limits</button><button type="button" className="button" onClick={() => setDraft({})}>Cancel</button></div>}
    </section>
  )
}
