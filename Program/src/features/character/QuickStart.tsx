import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient, type QueryClient, type UseQueryResult } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { ApiError, api } from '../../api'
import type { View } from '../../companion'
import type { CharacterDefinition, CitySummary, Connection, Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { RELATIONSHIPS, guessTimezone, stageNames } from './definition'
import { PasteCharacter } from './PasteCharacter'
import type { SplitResult } from './helper'
import { defaultCity } from './places'
import { CityOptions } from '../world/CityOptions'
import type { FeaturedCities } from '../world/cityText'
import { AGES, VIBES, emptyRequest, toggleVibe, turnedDown, vibeList, type DraftRequest, type DraftResult } from './drafting'
import { CitiesUnavailable } from '../world/CitiesUnavailable'
import { COMPANION_KEY } from '../../companion'
import type { Companion } from '../../types'
import { isActive } from '../ready/readyText'
import { queueWriteUp, useReady } from '../ready/useReady'
import { useWorlds } from '../worlds/useWorlds'
import { useKept } from './keptDraft'
import type { World } from '../../types'

const submitLabel = (busy: boolean, downloading: boolean) => busy ? (downloading ? 'Saving…' : 'Writing…') : downloading ? 'Create them now' : 'Create my companion'

/** Saves the picks as the companion now and queues the write-up for when the model is ready (companion/ready_writeup.py). */
async function saveForLater(client: QueryClient, body: Omit<DraftRequest, 'starting_closeness'>, starting_closeness: number): Promise<View> {
  const saved = await api<Companion>('/companion', { name: body.name, relationship: body.relationship, home_city: body.home_city, timezone: body.timezone, starting_closeness })
  client.setQueryData(COMPANION_KEY, saved)
  await queueWriteUp(client, { ...body, name: saved.version.name })
  return 'conversation'
}

/** Where they live unless the user picks: a new world's own city (Worlds), else a city near the user. */
function startingCity(world: World | undefined, cities: CitySummary[], timezone: string, another?: Props['another']): string {
  if (another) return another.city
  return world && !world.first ? world.city_id : defaultCity(cities, timezone)
}

/** Saving now and writing the rest later is only for a first companion, while "Set it up for me" downloads. */
function savesForLater(connected: boolean, ready: ReturnType<typeof useReady>['data'], another?: Props['another']): boolean {
  return !another && !connected && isActive(ready)
}

interface Props {
  onDraft: (definition: CharacterDefinition) => void; onSplit: (result: SplitResult) => void; onManual: () => void; go: (view: View) => void
  /** Another companion beside the main character (AnotherCompanion.tsx): they start in the main character's city and
   * time zone, the picks are not kept, and nothing is saved before the form. */
  another?: { name: string; city: string; timezone: string }
}

/** Three picks (name, age, where and when); the configured model drafts the rest for the form to review.
 * The idea, relationship, vibe and emotional edges wait under "More options". */
export function QuickStart({ onDraft, onSplit, onManual, go, another }: Props) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  // Kept while they step away, to Settings say, and come back (keptDraft.ts).
  const [picks, setPicks] = useKept('picks', () => ({ request: emptyRequest(another ? another.timezone : guessTimezone()), cityPicked: false }), !another)
  // The app picks where they live until the user picks somewhere else (or "Anywhere"): in a new world, its city.
  const { request, cityPicked } = picks
  const world = useWorlds().data?.world
  const homeCity = cityPicked ? request.home_city : startingCity(world, cities.data ?? [], request.timezone, another)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<{ text: string; settings: boolean } | null>(null)
  const set = (change: Partial<DraftRequest>) => setPicks((current) => ({ ...current, request: { ...current.request, ...change } }))
  const connected = !!connection.data
  // While "Set it up for me" downloads, they can save them now and the model writes the rest when it is ready.
  const ready = useReady().data
  const downloading = savesForLater(connected, ready, another)
  const client = useQueryClient()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const { starting_closeness, ...body } = request
      if (downloading) { go(await saveForLater(client, { ...body, home_city: homeCity }, starting_closeness)); return }
      onDraft({ ...(await api<DraftResult>('/companion/draft', { ...body, home_city: homeCity })).definition, starting_closeness })
    } catch (failure) {
      setError({ text: failure instanceof Error ? failure.message : 'The draft could not be written.', settings: failure instanceof ApiError && failure.code === 'provider' })
    } finally { setBusy(false) }
  }

  return (<>
    <section className="quick-start" aria-labelledby="quick-start-title">
      <h2 id="quick-start-title"><Sparkles aria-hidden="true" />Three things to start</h2>
      <p className="subtle">Your text model writes the rest: their job, week, skills, flaws and how they talk. You see the whole character before anything is saved.</p>
      <ModelNotice shown={connection.isSuccess && !connected} downloading={downloading} go={go} />
      <form className="form-stack" onSubmit={submit}>
        <Picks request={request} set={set} cities={cities} homeCity={homeCity} near={another ? `Where ${another.name} lives` : 'Picked near you'} pickCity={(home_city) => setPicks((current) => ({ cityPicked: true, request: { ...current.request, home_city } }))} />
        <details className="advanced more-options">
          <summary>More options</summary>
          <div className="form-stack">
            <TextArea label="Who are they?" value={request.idea} onChange={(idea) => set({ idea })} maxLength={2000} rows={2}
              placeholder="A night-shift nurse who is trying to get back into running" hint="Leave it empty to be surprised." />
            <Field label="Relationship" hint="Friendship unless you pick otherwise, someone you haven't met yet too. Romance is only ever your choice.">
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
        {error && <DraftError error={error} go={go} onManual={onManual} />}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={!(connected || downloading) || busy}>{submitLabel(busy, downloading)}</button>
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
  /** Where the city comes from unless they choose. */
  near: string
}

function Picks({ request, set, cities, homeCity, near, pickCity }: PicksProps) {
  const featured = useQuery({ queryKey: ['featured-cities'], queryFn: () => api<FeaturedCities<CitySummary>>('/world/featured'), staleTime: Infinity })
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
      <Field label="Where and when" hint={`${near} unless you choose. Their days use its real places, and its era.`}>
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={homeCity} onChange={(event) => pickCity(event.target.value)}>
            <option value="">Anywhere, today</option>
            <CityOptions cities={cities.data ?? []} featured={featured.data?.cities} withRegion />
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

/** A service that turned the request down can be put right in Settings; the picks wait here (keptDraft.ts). */
function DraftError({ error, go, onManual }: { error: { text: string; settings: boolean }; go: (view: View) => void; onManual: () => void }) {
  if (!error.settings) return <Notice tone="error" action={<button type="button" className="text-button" onClick={onManual}>Fill in the form myself</button>}>{error.text}</Notice>
  return <Notice tone="error">{turnedDown(error.text)}
    <button type="button" className="text-button notice-link" onClick={() => go('settings/models')}>Open Settings</button>
  </Notice>
}


function ModelNotice({ shown, downloading, go }: { shown: boolean; downloading: boolean; go: (view: View) => void }) {
  if (downloading) return <Notice>Your model isn't ready yet. Create them now and it writes the rest when it's ready.</Notice>
  if (!shown) return null
  return <Notice action={<button type="button" className="text-button inline" onClick={() => go('settings/models')}>Open Settings</button>}>Drafting uses your text model, and none is connected yet. You can still fill in the form yourself.</Notice>
}
