import { useState, type FormEvent } from 'react'
import type { Layer, Memory, PlanStatus } from '../../types'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { LAYERS, titleFrom, type RememberRequest } from './memoryGroups'

export interface NewMemory {
  layer: Layer
  subject: string
  value: string
  reality: 'real' | 'fiction'
  boundary: boolean
  sensitive: boolean
  plan_status: PlanStatus | null
  applies_until: string | null
  source_message_ids: string[]
}

export function RememberForm({ name, request, onSave, onCancel }: { name: string; request: RememberRequest | null; onSave: (memory: NewMemory) => Promise<Memory | string>; onCancel: () => void }) {
  const [layer, setLayer] = useState<Layer>(request?.layer ?? 'user_fact')
  const [subject, setSubject] = useState('')
  const [value, setValue] = useState(request?.text.slice(0, 4000) ?? '')
  const [boundary, setBoundary] = useState(false)
  const [sensitive, setSensitive] = useState(false)
  const [planStatus, setPlanStatus] = useState<PlanStatus>('proposed')
  const [until, setUntil] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Never a silently greyed-out button: a missing value says so here, and a refusal is shown under the form.
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim()) { setError('Write what to remember first.'); return }
    setSaving(true)
    const saved = await onSave(newMemory({ layer, subject, value, boundary, sensitive, planStatus, until, request }))
    setSaving(false)
    if (typeof saved === 'string') setError(saved)
    else onCancel()
  }
  return (
    <form className="remember-form form-stack" onSubmit={submit} aria-label="Remember something">
      <h2>Remember something</h2>
      {request && <FromMessage request={request} />}
      <div className="form-grid">
        <Field label="Kind" hint={LAYERS.find((item) => item.id === layer)?.hint}>
          {(id, hint) => <select id={id} aria-describedby={hint} value={layer} autoFocus onChange={(event) => setLayer(event.target.value as Layer)}>{LAYERS.map((item) => <option key={item.id} value={item.id}>{item.title(name)}</option>)}</select>}
        </Field>
        <TextInput label="About (optional)" value={subject} onChange={setSubject} maxLength={200} placeholder="Nickname, Home city, Sister's name" hint="A short title for what it is about. Left empty, the first words are used." />
      </div>
      <TextArea label="What to remember" value={value} onChange={setValue} maxLength={4000} rows={2} hint="Write it as a plain fact, such as Lives in Chicago." />
      <TimingFields layer={layer} planStatus={planStatus} setPlanStatus={setPlanStatus} until={until} setUntil={setUntil} />
      {layer !== 'companion_life' && <>
        <Toggle label="This is a boundary" hint="Always respected, however old it is." checked={boundary} onChange={setBoundary} />
        <Toggle label="Sensitive" hint="Health, relationships, money and similar personal details." checked={sensitive} onChange={setSensitive} />
      </>}
      {error && <Notice tone="error">{error}</Notice>}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving}>Remember</button>
        <button type="button" className="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function newMemory({ layer, subject, value, boundary, sensitive, planStatus, until, request }: { layer: Layer; subject: string; value: string; boundary: boolean; sensitive: boolean; planStatus: PlanStatus; until: string; request: RememberRequest | null }): NewMemory {
  const fiction = layer === 'companion_life'
  return {
    layer, subject: subject.trim() || titleFrom(value), value: value.trim(), reality: fiction ? 'fiction' : 'real', boundary: boundary && !fiction, sensitive: sensitive && !fiction,
    plan_status: layer === 'plan' ? planStatus : null, applies_until: until ? new Date(`${until}T23:59:59`).toISOString() : null,
    source_message_ids: request ? [request.messageId] : [],
  }
}

function TimingFields({ layer, planStatus, setPlanStatus, until, setUntil }: { layer: Layer; planStatus: PlanStatus; setPlanStatus: (status: PlanStatus) => void; until: string; setUntil: (value: string) => void }) {
  if (layer !== 'plan' && layer !== 'temporary') return null
  return <>
    {layer === 'plan' && (
      <Field label="Status" hint="A plan stays open until it is marked completed or cancelled. A date passing does not finish it.">
        {(id, hint) => <select id={id} aria-describedby={hint} value={planStatus} onChange={(event) => setPlanStatus(event.target.value as PlanStatus)}>
          {['proposed', 'agreed', 'postponed', 'completed', 'cancelled'].map((status) => <option key={status} value={status}>{status[0].toUpperCase() + status.slice(1)}</option>)}
        </select>}
      </Field>
    )}
    <TextInput label="Applies until (optional)" type="date" value={until} onChange={setUntil} hint="After this day it is no longer treated as current. It stays in Memories." />
  </>
}

function FromMessage({ request }: { request: RememberRequest }) {
  const text = request.text.length > 200 ? `${request.text.slice(0, 200)}…` : request.text
  return <p className="subtle">From {request.from ? `${request.from}'s` : 'your'} message: <q>{text}</q>. Write it the way it should be remembered.</p>
}
