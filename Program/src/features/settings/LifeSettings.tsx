import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { LifeSettings as Limits } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { DRAMA_LEVELS } from '../today/storyText'

const KEY = ['life-settings']
type NumberKey = 'catch_up_max_events' | 'catch_up_lookback_hours' | 'return_gap_hours' | 'background_interval_minutes' | 'background_daily_events' | 'texts_daily' | 'texts_gap_hours' | 'circle_size'

const LIMITS: { key: NumberKey; label: string; min: number; max: number; hint: string }[] = [
  { key: 'catch_up_max_events', label: 'Most events when you return', min: 0, max: 6, hint: 'However long you were away.' },
  { key: 'catch_up_lookback_hours', label: 'How far back to fill in (hours)', min: 6, max: 336, hint: 'Older time away stays quiet.' },
  { key: 'return_gap_hours', label: 'Time away before catching up (hours)', min: 1, max: 48, hint: '' },
  { key: 'background_interval_minutes', label: 'Minutes between background updates', min: 15, max: 1440, hint: '' },
  { key: 'background_daily_events', label: 'Most background events a day', min: 0, max: 8, hint: '' },
  { key: 'texts_daily', label: 'Most first messages a day', min: 1, max: 6, hint: '' },
  { key: 'texts_gap_hours', label: 'Quiet hours after talking before they message first', min: 1, max: 24, hint: '' },
  { key: 'circle_size', label: 'People in their circle', min: 0, max: 12, hint: '0 decides by how sociable they are: 4 for a homebody, 5 usually, 10 for a social butterfly. Add people from Today.' },
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
      <Toggle label="Catch up when you return" checked={data.catch_up_on_return} onChange={(value) => void save({ catch_up_on_return: value })}
        hint="Off: nothing is written for the time you were away, and their life picks up from when you return." />
      <Toggle label="Add everyday events without asking" checked={data.automatic_events} onChange={(value) => void save({ automatic_events: value })}
        hint="Off: new events wait in Today for you to keep or discard. Big changes to who they are or your relationship always wait for you." />
      <Toggle label="Let the model word their days" checked={data.phrase_with_model} onChange={(value) => void save({ phrase_with_model: value })}
        hint="What happens is always built from their routine and city. With this on, your model rewrites it in their voice; off, plain wording is used and no model calls are made." />
      <Toggle label={`Let ${name} message you first`} checked={data.texts_first} onChange={(value) => void save({ texts_first: value })}
        hint={`${name} may start a conversation: to check in on a break or after work, to ask about something they said they'd ask about, how a plan of yours went, to share news from their day, or when something reminds them of you. Never during your quiet hours, while they sleep or twice without an answer.`} />
      <Toggle label={`Reply at ${name}'s pace`} checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When ${name} is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake. Turn off for replies right away.`} />
      <Toggle label={`Let ${name}'s days go off plan`} checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then ${name} runs late, stays late, has plans fall through, has something come up or gets a surprise visit. Rolled with fixed dice, so a day never changes after the fact.`} />
      <BirthdayField saved={data.user_birthday} onSave={(value) => save({ user_birthday: value }, value ? 'Birthday saved.' : 'Birthday forgotten.')} name={name} />
      <DramaSlider name={name} value={data.drama} onChange={(value) => void save({ drama: value })} />
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

/** Realistic to soap opera: how often things happen in their world and how far they go. */
function DramaSlider({ name, value, onChange }: { name: string; value: number; onChange: (value: number) => void }) {
  const level = DRAMA_LEVELS[value] ?? DRAMA_LEVELS[1]
  return (
    <Field label={`Drama in ${name}'s world: ${level.label}`} hint={`${level.hint} Storylines in their life and their people's, from quiet to soap opera.`}>
      {(id, describedBy) => <input id={id} type="range" min={0} max={3} step={1} value={value} aria-valuetext={level.label} aria-describedby={describedBy}
        onChange={(event) => onChange(Number(event.target.value))} />}
    </Field>
  )
}

/** The user's own birthday ("MM-DD"): noticed when they say it in chat, changed or forgotten here. */
function BirthdayField({ name, saved, onSave }: { name: string; saved: string; onSave: (value: string) => Promise<boolean> }) {
  const [value, setValue] = useState<string | null>(null)
  const shown = value ?? saved
  return (
    <form className="form-stack" onSubmit={(event) => { event.preventDefault(); void onSave(shown.trim()).then((done) => { if (done) setValue(null) }) }}>
      <TextInput label="Your birthday" value={shown} maxLength={5} placeholder="MM-DD" onChange={setValue}
        hint={`Month and day, such as 03-14. ${name} remembers it on the day. Filled in when you mention it in chat; clear it to have it forgotten.`} />
      {value !== null && value !== saved && <div className="form-actions"><button type="submit" className="button primary">Save birthday</button><button type="button" className="button" onClick={() => setValue(null)}>Cancel</button></div>}
    </form>
  )
}
