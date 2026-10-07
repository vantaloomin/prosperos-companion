import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CharacterDefinition, CitySummary, Connection, Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { RELATIONSHIPS, guessTimezone } from './definition'
import { PasteCharacter } from './PasteCharacter'
import type { SplitResult } from './helper'
import { AGES, VIBES, emptyRequest, toggleVibe, vibeList, type DraftRequest, type DraftResult } from './drafting'

interface Props { onDraft: (definition: CharacterDefinition) => void; onSplit: (result: SplitResult) => void; onManual: () => void; go: (view: View) => void }

/** A line or two and a few picks; the configured model drafts the rest for the form to review. */
export function QuickStart({ onDraft, onSplit, onManual, go }: Props) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const [request, setRequest] = useState<DraftRequest>(() => emptyRequest(guessTimezone()))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (change: Partial<DraftRequest>) => setRequest((current) => ({ ...current, ...change }))
  const connected = !!connection.data

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      onDraft((await api<DraftResult>('/companion/draft', request)).definition)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The draft could not be written.')
    } finally { setBusy(false) }
  }

  return (<>
    <section className="quick-start" aria-labelledby="quick-start-title">
      <h2 id="quick-start-title"><Sparkles aria-hidden="true" />Start with an idea</h2>
      <p className="subtle">Describe them in a line or two and your text model drafts the rest: their job, week, skills, flaws and how they talk. Everything is optional, and you review the whole draft before anything is saved.</p>
      {connection.isSuccess && !connected && (
        <Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Settings</button>}>Drafting uses your text model, and none is connected yet. You can still fill in the form yourself.</Notice>
      )}
      <form className="form-stack" onSubmit={submit}>
        <TextArea label="Who are they?" value={request.idea} onChange={(idea) => set({ idea })} maxLength={2000} rows={2}
          placeholder="A night-shift nurse who is trying to get back into running" hint="Leave it empty to be surprised." />
        <Picks request={request} set={set} />
        <Vibes vibe={request.vibe} onChange={(vibe) => set({ vibe })} />
        <Toggle label="Give them emotional edges" checked={request.emotional_edges} onChange={(emotional_edges) => set({ emotional_edges })}
          hint="Such as jealousy or missing you when you are away. Off unless you turn it on, and you can change it later." />
        {busy && <Notice>Writing a draft. A local model can take a minute or two.</Notice>}
        {error && <Notice tone="error" action={<button type="button" className="text-button" onClick={onManual}>Fill in the form myself</button>}>{error}</Notice>}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={!connected || busy}>{busy ? 'Drafting…' : 'Draft my companion'}</button>
          <button type="button" className="text-button" onClick={onManual}>Fill in the form myself</button>
        </div>
      </form>
    </section>
    <PasteCharacter connected={connected} onSplit={onSplit} />
  </>)
}

function Picks({ request, set }: { request: DraftRequest; set: (change: Partial<DraftRequest>) => void }) {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  return (
    <div className="form-grid">
      <TextInput label="Name (optional)" value={request.name} onChange={(name) => set({ name })} maxLength={120} hint="Left empty, the draft suggests one." />
      <Field label="Relationship" hint="Romance is only ever your choice.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={request.relationship} onChange={(event) => set({ relationship: event.target.value as Relationship })}>
            {RELATIONSHIPS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        )}
      </Field>
      <Field label="Age" hint="Companions are always adults.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={request.age} onChange={(event) => set({ age: event.target.value })}>
            {AGES.map((age) => <option key={age.value} value={age.value}>{age.label}</option>)}
          </select>
        )}
      </Field>
      <Field label="Home city" hint="Their days use its real neighbourhoods and places.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={request.home_city} onChange={(event) => set({ home_city: event.target.value })}>
            <option value="">None</option>
            {(cities.data ?? []).map((city) => <option key={city.id} value={city.id}>{city.name}, {city.region}</option>)}
          </select>
        )}
      </Field>
    </div>
  )
}

function Vibes({ vibe, onChange }: { vibe: string; onChange: (vibe: string) => void }) {
  const chosen = vibeList(vibe).map((item) => item.toLowerCase())
  return (
    <div className="vibes">
      <TextInput label="Vibe (optional)" value={vibe} onChange={onChange} maxLength={300} hint="Pick a few below or write your own, separated by commas." />
      <div className="vibe-picks" role="group" aria-label="Vibe suggestions">
        {VIBES.map((pick) => (
          <button key={pick} type="button" className="vibe-pick" aria-pressed={chosen.includes(pick.toLowerCase())} onClick={() => onChange(toggleVibe(vibe, pick))}>{pick}</button>
        ))}
      </div>
    </div>
  )
}
