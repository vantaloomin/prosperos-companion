import { useState, type FormEvent } from 'react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CharacterDefinition, CitySummary, Connection, Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { RELATIONSHIPS, guessTimezone, stageNames } from './definition'
import { PasteCharacter } from './PasteCharacter'
import type { SplitResult } from './helper'
import { defaultCity } from './places'
import { CityOptions } from '../world/CityOptions'
import { AGES, VIBES, emptyRequest, toggleVibe, vibeList, type DraftRequest, type DraftResult } from './drafting'
import { CitiesUnavailable } from '../world/CitiesUnavailable'

interface Props { onDraft: (definition: CharacterDefinition) => void; onSplit: (result: SplitResult) => void; onManual: () => void; go: (view: View) => void }

/** Three picks (name, age, where and when); the configured model drafts the rest for the form to review.
 * The idea, relationship, vibe and emotional edges wait under "More options". */
export function QuickStart({ onDraft, onSplit, onManual, go }: Props) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const [request, setRequest] = useState<DraftRequest>(() => emptyRequest(guessTimezone()))
  // The app picks where they live until the user picks somewhere else (or "Anywhere").
  const [cityPicked, setCityPicked] = useState(false)
  const homeCity = cityPicked ? request.home_city : defaultCity(cities.data ?? [], request.timezone)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (change: Partial<DraftRequest>) => setRequest((current) => ({ ...current, ...change }))
  const connected = !!connection.data

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { starting_closeness, ...body } = request
      onDraft({ ...(await api<DraftResult>('/companion/draft', { ...body, home_city: homeCity })).definition, starting_closeness })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The draft could not be written.')
    } finally { setBusy(false) }
  }

  return (<>
    <section className="quick-start" aria-labelledby="quick-start-title">
      <h2 id="quick-start-title"><Sparkles aria-hidden="true" />Three things to start</h2>
      <p className="subtle">Your text model writes the rest: their job, week, skills, flaws and how they talk. You see the whole character before anything is saved.</p>
      {connection.isSuccess && !connected && (
        <Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Settings</button>}>Drafting uses your text model, and none is connected yet. You can still fill in the form yourself.</Notice>
      )}
      <form className="form-stack" onSubmit={submit}>
        <Picks request={request} set={set} cities={cities} homeCity={homeCity} pickCity={(home_city) => { setCityPicked(true); set({ home_city }) }} />
        <details className="advanced more-options">
          <summary>More options</summary>
          <div className="form-stack">
            <TextArea label="Who are they?" value={request.idea} onChange={(idea) => set({ idea })} maxLength={2000} rows={2}
              placeholder="A night-shift nurse who is trying to get back into running" hint="Leave it empty to be surprised." />
            <Field label="Relationship" hint="Friendship unless you pick otherwise. Romance is only ever your choice.">
              {(id, hint) => (
                <select id={id} aria-describedby={hint} value={request.relationship} onChange={(event) => set({ relationship: event.target.value as Relationship })}>
                  {RELATIONSHIPS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              )}
            </Field>
            <Field label="How close you start" hint="Just met unless you pick otherwise. It grows from here as you talk.">
              {(id, hint) => (
                <select id={id} aria-describedby={hint} value={request.starting_closeness} onChange={(event) => set({ starting_closeness: Number(event.target.value) })}>
                  {stageNames(request.relationship).map((stage, index) => <option key={stage} value={index + 1}>{stage}</option>)}
                </select>
              )}
            </Field>
            <Vibes vibe={request.vibe} onChange={(vibe) => set({ vibe })} />
            <Toggle label="Give them emotional edges" checked={request.emotional_edges} onChange={(emotional_edges) => set({ emotional_edges })}
              hint="Such as jealousy or missing you when you are away. Off unless you turn it on, and you can change it later." />
          </div>
        </details>
        {busy && <Notice>Writing your companion. A local model can take a minute or two.</Notice>}
        {error && <Notice tone="error" action={<button type="button" className="text-button" onClick={onManual}>Fill in the form myself</button>}>{error}</Notice>}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={!connected || busy}>{busy ? 'Writing…' : 'Create my companion'}</button>
          <button type="button" className="text-button" onClick={onManual}>Fill in the form myself</button>
        </div>
      </form>
    </section>
    <PasteCharacter connected={connected} onSplit={onSplit} />
  </>)
}

interface PicksProps {
  request: DraftRequest; set: (change: Partial<DraftRequest>) => void
  cities: UseQueryResult<CitySummary[]>; homeCity: string; pickCity: (id: string) => void
}

function Picks({ request, set, cities, homeCity, pickCity }: PicksProps) {
  return (<>
    <div className="form-grid three">
      <TextInput label="Name" value={request.name} onChange={(name) => set({ name })} maxLength={120} hint="Optional. Left empty, they get one that fits." />
      <Field label="Age" hint="Companions are always adults.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={request.age} onChange={(event) => set({ age: event.target.value })}>
            {AGES.map((age) => <option key={age.value} value={age.value}>{age.label}</option>)}
          </select>
        )}
      </Field>
      <Field label="Where and when" hint="Picked near you unless you choose. Their days use its real places, and its era.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={homeCity} onChange={(event) => pickCity(event.target.value)}>
            <option value="">Anywhere, today</option>
            <CityOptions cities={cities.data ?? []} withRegion />
          </select>
        )}
      </Field>
    </div>
    <CitiesUnavailable cities={cities} />
  </>)
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
