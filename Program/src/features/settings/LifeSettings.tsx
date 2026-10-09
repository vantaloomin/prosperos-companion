import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatList, LifeSettings as Limits } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { PresetSelect, SliderField, Stepper } from '../../components/NumberFields'
import { countText, hoursText, minutesText } from '../../components/numberBounds'
import { DRAMA_LEVELS } from '../today/storyText'
import { SectionPending } from '../../components/SectionPending'

const KEY = ['life-settings']
type NumberKey = 'catch_up_max_events' | 'catch_up_lookback_hours' | 'return_gap_hours' | 'background_interval_minutes' | 'background_daily_events' | 'texts_daily' | 'away_daily' | 'texts_gap_hours' | 'circle_size' | 'recap_after_days'

type Format = (value: number) => string
const counted = (one: string, many: string, zero?: string): Format => (value) => countText(value, one, many, zero)
const every: Format = (minutes) => ({ 60: 'Every hour', 1440: 'Once a day' })[minutes] ?? `Every ${minutesText(minutes)}`

// Iris's number controls (/mnt/project-files/companion-design/number-controls.md): steppers for small counts,
// a slider for a wide one, friendly presets for time spans. Each saves on change; the server still checks the range.
const STEPPERS: { name: NumberKey; label: string; min: number; max: number; format: Format; hint?: string }[] = [
  { name: 'catch_up_max_events', label: 'Most events when you return', min: 0, max: 6, format: counted('event', 'events', 'None'), hint: 'However long you were away.' },
  { name: 'background_daily_events', label: 'Most background events a day', min: 0, max: 8, format: counted('event', 'events', 'None') },
  { name: 'texts_daily', label: 'Most first messages a day, each', min: 1, max: 6, format: counted('message', 'messages') },
  { name: 'circle_size', label: 'People in their circle', min: 0, max: 12, format: counted('person', 'people', 'Automatic'), hint: 'Automatic decides by how sociable they are: 4 for a homebody, 5 usually, 10 for a social butterfly. Add people from Today.' },
]
const PRESETS: { name: NumberKey; label: string; presets: number[]; format: Format; hint?: string }[] = [
  { name: 'catch_up_lookback_hours', label: 'How far back to fill in', presets: [6, 12, 24, 48, 72, 168, 336], format: hoursText, hint: 'Older time away stays quiet.' },
  { name: 'return_gap_hours', label: 'Time away before catching up', presets: [1, 2, 4, 8, 12, 24, 48], format: hoursText },
  { name: 'background_interval_minutes', label: 'Background updates', presets: [15, 30, 60, 120, 240, 480, 1440], format: every },
  { name: 'texts_gap_hours', label: 'Quiet hours after talking before they message first', presets: [1, 2, 3, 4, 6, 8, 12, 24], format: hoursText },
  { name: 'recap_after_days', label: 'Time away before a "While you were away" catch-up', presets: [0, 1, 2, 3, 5, 7, 14, 30, 60], format: counted('day', 'days', 'Off'), hint: 'Shown once in the chat when you come back: what happened in their life and around town.' },
]

export function LifeSettings({ name }: { name: string }) {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: KEY, queryFn: () => api<Limits>('/life/settings') })
  const others = (useQuery({ queryKey: CHATS_KEY, queryFn: () => api<ChatList>('/chats') }).data?.chats.length ?? 1) > 1
  const [pending, setPending] = useState<Partial<Limits>>({})
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
  if (!settings.data) return <SectionPending queries={[settings]} heading="life-heading" title={`${name}'s life`} />
  const data = { ...settings.data, ...pending }
  const saveNumber = (key: NumberKey, value: number) => void save({ [key]: value }, 'Saved.')
  return (
    <section className="settings-section form-stack" aria-labelledby="life-heading">
      <div>
        <h2 id="life-heading">{name}'s life</h2>
        <p className="subtle">When you come back, a few things that fit {name}'s routine are written for the time you were away. Nothing is written for time while paused.</p>
      </div>
      <Toggle label="Catch up when you return" checked={data.catch_up_on_return} onChange={(value) => void save({ catch_up_on_return: value })}
        hint="Off: nothing is written for the time you were away, and their life picks up from when you return." />
      <Toggle label="Add everyday events without asking" checked={data.automatic_events} onChange={(value) => void save({ automatic_events: value })}
        hint="On unless you turn it off: their days just happen, and you can correct anything afterwards. Off: new events wait in Today for you to keep or discard." />
      <Toggle label="Let the model word their days" checked={data.phrase_with_model} onChange={(value) => void save({ phrase_with_model: value })}
        hint="What happens is always built from their routine and city. With this on, your model rewrites it in their voice; off, plain wording is used and no model calls are made." />
      <Toggle label={others ? `Let ${name} and your other companions message you first` : `Let ${name} message you first`} checked={data.texts_first} onChange={(value) => void save({ texts_first: value })}
        hint={`${name} may start a conversation: to check in on a break or after work, to ask about something they said they'd ask about, how a plan of yours went, to share news from their day, or when something reminds them of you. Never during your quiet hours, while they sleep or twice without an answer.${others ? ' Your other companions do too, even while you are chatting with someone else.' : ''}`} />
      <Toggle label={`Reply at ${name}'s pace`} checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When ${name} is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake. In group chats, each reply shows after the time it would take to read and type it, one after another. Turn off for replies right away.`} />
      <Toggle label={`Let ${name}'s days go off plan`} checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then ${name} runs late, stays late, has plans fall through, has something come up or gets a surprise visit. Rolled with fixed dice, so a day never changes after the fact.`} />
      <BirthdayField saved={data.user_birthday} onSave={(value) => save({ user_birthday: value }, value ? 'Birthday saved.' : 'Birthday forgotten.')} name={name} />
      <DramaSlider name={name} value={data.drama} onChange={(value) => void save({ drama: value })} />
      <div className="form-grid">
        {STEPPERS.map((item) => <Stepper key={item.name} {...item} value={data[item.name]} onChange={(value) => saveNumber(item.name, value)} />)}
        <SliderField label="Most first messages a day, all companions together" value={data.away_daily} min={0} max={40} format={counted('message', 'messages', 'Off')}
          hint="Shared by every companion, so a day with the app left running stays within what you want to spend on your model." onChange={(value) => saveNumber('away_daily', value)} />
        {PRESETS.map((item) => <PresetSelect key={item.name} {...item} value={data[item.name]} onChange={(value) => saveNumber(item.name, value)} />)}
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Realistic to soap opera: how often things happen in their world and how far they go. */
function DramaSlider({ name, value, onChange }: { name: string; value: number; onChange: (value: number) => void }) {
  const level = DRAMA_LEVELS[value] ?? DRAMA_LEVELS[1]
  return (
    <Field label={`Drama in ${name}'s world: ${level.label}`} hint={level.hint}>
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
