import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Copy, Eye, Globe, History, Pause, Plus, Trash2, UserRound, UserRoundPlus } from 'lucide-react'
import { api } from '../../api'
import type { Persona, World, Worlds as WorldsData } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { PersonaForm } from './PersonaForm'
import { CityPick, SOMEWHERE_NEW } from './CityPick'
import { enter, useWorlds, WORLDS_KEY } from './useWorlds'
import { companionsLine, copyLabel, copyNote, initial, personaName, personaRef, personaRefTagged, defaultPastYear, pastYears, pausedNote, personaSuffix, personaTitle, worldTag, yearBadge } from './worldsText'
import { Field, Toggle } from '../../components/Fields'
import { useWatchActions } from '../watch/useObserver'

type Run = (action: () => Promise<unknown>) => Promise<void>

/** Worlds and personas: who the user is, the worlds each persona lives in, and switching between them. */
export function Worlds() {
  const worlds = useWorlds()
  const client = useQueryClient()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [making, setMaking] = useState(false)
  // A copy just made (Iris): its section scrolls into view, lights up briefly and takes focus.
  const [arrived, setArrived] = useState('')
  const run: Run = async (action) => {
    if (busy) return
    setError('')
    try { await action() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') } finally { setBusy('') }
  }
  const switchTo = (path: string, label: string) => { setBusy(label); return run(async () => { await api(path, {}); enter() }) }
  const store = (data: WorldsData) => client.setQueryData(WORLDS_KEY, data)
  const loaded = !!worlds.data
  useEffect(() => { if (loaded && window.history.state?.focus === 'persona-home') toHomeCity() }, [loaded])
  if (worlds.isPending) return <Loading label="Loading your worlds" />
  if (worlds.isError) return <ErrorNotice error={worlds.error} />
  const data = worlds.data
  return (
    <section className="worlds" aria-labelledby="worlds-heading">
      <header className="worlds-header">
        <h1 id="worlds-heading">Worlds</h1>
        <p className="subtle">{personaName(data.persona) ? <>You are <strong>{personaName(data.persona)}</strong> in </> : <>You're in </>}<strong>{data.world.name}</strong>. Each persona lives in their own worlds, with their own companions, town and history. Your settings and models come with you everywhere. Only the world you're in moves on. The others wait for you.</p>
        {busy && <Notice>Opening {busy}…</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
      </header>
      <div className="worlds-list">
        {data.personas.map((persona) => {
          const tag = worldTag(persona, data.personas)
          return <PersonaWorlds key={persona.id} persona={persona} tag={tag} cityId={data.world.city_id} run={run} store={store}
            arrived={arrived === persona.id} onCopied={setArrived}
            onSwitch={(world) => void switchTo(`/worlds/${world.id}/switch`, world.name)}
            onSwitchPersona={() => void switchTo(`/worlds/personas/${persona.id}/switch`, personaRefTagged(persona, tag))} />
        })}
        {making
          ? <PersonaForm cityId={data.world.city_id} kinds={data.persona.kind_shown} onCancel={() => setMaking(false)} onSaved={() => { setMaking(false); void client.invalidateQueries({ queryKey: WORLDS_KEY }) }} />
          : <div className="form-actions">
              <button type="button" className="button" onClick={() => setMaking(true)}><UserRoundPlus aria-hidden="true" />New persona</button>
            </div>}
        <div id="persona-edit"><PersonaForm key={`${data.persona.id}:${data.world.id}`} persona={data.persona} world={data.world} cityId={data.world.city_id} onSaved={(saved) => { if (saved) store(saved) }} /></div>
      </div>
    </section>
  )
}

/** Where you live, on the persona form (opened from "Change your home city" on the Character page). */
function toHomeCity() {
  const field = document.querySelector<HTMLSelectElement>('#persona-edit .persona-home select')
  field?.scrollIntoView({ block: 'center' })
  field?.focus()
}

/** The edit form for the persona the user is now, at the end of the page: go there with its name box ready. */
function addName() {
  const field = document.querySelector<HTMLInputElement>('#persona-edit input')
  field?.scrollIntoView({ block: 'center' })
  field?.focus()
}

interface PersonaWorldsProps {
  persona: Persona; cityId: string; run: Run; store: (data: WorldsData) => void; onSwitch: (world: World) => void; onSwitchPersona: () => void
  /** Their world when another persona has the same name (worldsText `worldTag`). */
  tag: string
  /** A copy just made: show it. `onCopied` names the copy this persona's form made. */
  arrived: boolean; onCopied: (id: string) => void
}

function PersonaWorlds({ persona, tag, cityId, run, store, arrived, onCopied, onSwitch, onSwitchPersona }: PersonaWorldsProps) {
  const [deleting, setDeleting] = useState(false)
  const [adding, setAdding] = useState<'' | 'world' | 'copy'>('')
  const addLink = useRef<HTMLButtonElement>(null)
  const copyLink = useRef<HTMLButtonElement>(null)
  // Closing a form puts focus back on the link that opened it.
  const closeAdding = () => { const link = adding === 'copy' ? copyLink : addLink; setAdding(''); requestAnimationFrame(() => link.current?.focus()) }
  const removable = !persona.active && persona.worlds.every((world) => !world.first)
  const section = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!arrived) return
    section.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    section.current?.querySelector<HTMLElement>('h2')?.focus({ preventScroll: true })
  }, [arrived])
  const copied = (id: string) => { setAdding(''); onCopied(id) }
  return (
    <section ref={section} className={arrived ? 'persona-worlds arrived' : 'persona-worlds'} aria-label={tag ? `${personaTitle(persona)} (${tag})` : personaTitle(persona)}>
      <PersonaRow persona={persona} tag={tag} onSwitchPersona={onSwitchPersona} onDelete={removable ? () => setDeleting(true) : undefined} />
      <ul className="world-rows">
        {persona.worlds.map((world) => <WorldRow key={world.id} world={world} run={run} store={store} onSwitch={() => onSwitch(world)} />)}
      </ul>
      {adding === 'world' && <NewWorld persona={persona} cityId={cityId} run={run} onDone={closeAdding} />}
      {adding === 'copy' && <CopyPersona persona={persona} cityId={cityId} run={run} onDone={closeAdding} onCopied={copied} />}
      {!adding && <div className="persona-world-actions">
        <button ref={addLink} type="button" className="text-button" onClick={() => setAdding('world')}><Plus aria-hidden="true" />New world for {personaRef(persona)}</button>
        <button ref={copyLink} type="button" className="text-button" onClick={() => setAdding('copy')}><Copy aria-hidden="true" />{copyLabel(persona)}</button>
      </div>}
      {deleting && <ConfirmDialog title={`Delete ${personaRefTagged(persona, tag)}?`} onClose={() => setDeleting(false)} actions={<>
        <button type="button" className="button" onClick={() => setDeleting(false)}>Keep</button>
        <button type="button" className="button danger" onClick={() => void run(async () => { store(await api<WorldsData>(`/worlds/personas/${persona.id}`, undefined, 'DELETE')); setDeleting(false) })}>Delete</button>
      </>}>
        <p>Their {persona.worlds.length === 1 ? 'world goes' : `${persona.worlds.length} worlds go`} with them, with every companion and chat in it. A backup of each is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
    </section>
  )
}

/** Where the persona's new world is: somewhere new the app picks unless the user picks a city. */
function NewWorld({ persona, cityId, run, onDone }: { persona: Persona; cityId: string; run: Run; onDone: () => void }) {
  const client = useQueryClient()
  const [city, setCity] = useState(SOMEWHERE_NEW)
  const [making, setMaking] = useState<'' | 'make' | 'watch'>('')
  const [year, setYear] = useState<number | null>(null)
  // "Watch a city": the new world starts just watching (companion/observer.py).
  const make = (watch = false) => { setMaking(watch ? 'watch' : 'make'); return run(async () => {
    await api('/worlds', { persona_id: persona.id, city_id: city, watch, year })
    await client.invalidateQueries({ queryKey: WORLDS_KEY })
    onDone()
  }).finally(() => setMaking('')) }
  return (
    <form className="new-world form-stack" aria-label={`New world for ${personaRef(persona)}`} onSubmit={(event) => { event.preventDefault(); void make() }}
      onKeyDown={(event) => { if (event.key === 'Escape' && !making) onDone() }}>
      <CityPick value={city} currentId={cityId} disabled={!!making} autoFocus onChange={setCity} />
      <PastYear year={year} disabled={!!making} onChange={setYear} />
      <div className="form-actions wrap">
        <button type="submit" className="button primary" disabled={!!making}>{making === 'make' ? 'Making the world…' : 'Make this world'}</button>
        <button type="button" className="button" disabled={!!making} onClick={() => void make(true)}><Eye aria-hidden="true" />{making === 'watch' ? 'Making the world…' : 'Watch a city'}</button>
        <button type="button" className="text-button" disabled={!!making} onClick={onDone}>Cancel</button>
      </div>
      <p className="subtle">Watch a city: see the town go on without you, following whoever you like. Step in whenever you want.</p>
    </form>
  )
}

/** "Start in a past year" (companion/world_year.py): off, the world is in the present; on, the app offers ten years
 * back and the user can pick any year back to 1990. The clock runs in that year at real speed. */
function PastYear({ year, disabled, onChange }: { year: number | null; disabled: boolean; onChange: (year: number | null) => void }) {
  const thisYear = new Date().getFullYear()
  return (
    <div className="past-year form-stack">
      <Toggle label="Start in a past year" checked={year !== null} disabled={disabled} onChange={(on) => onChange(on ? defaultPastYear(thisYear) : null)}
        hint="Its calendar runs in that year at real speed, with the phones, prices, songs and jobs of the time." />
      {year !== null && <Field label="Year">
        {(id) => <select id={id} value={year} disabled={disabled} onChange={(event) => onChange(Number(event.target.value))}>
          {pastYears(thisYear).map((option) => <option key={option} value={option}>{option}</option>)}
        </select>}
      </Field>}
    </div>
  )
}

/** A separate copy of the persona, so the user need not type them again: a world of their own where they pick the
 * city (somewhere new unless they pick), with everything on the persona's form but where they live. */
function CopyPersona({ persona, cityId, run, onDone, onCopied }: { persona: Persona; cityId: string; run: Run; onDone: () => void; onCopied: (id: string) => void }) {
  const client = useQueryClient()
  const [city, setCity] = useState(SOMEWHERE_NEW)
  const [making, setMaking] = useState(false)
  const make = () => { setMaking(true); return run(async () => {
    const copy = await api<Persona>(`/worlds/personas/${persona.id}/copy`, { city_id: city })
    await client.invalidateQueries({ queryKey: WORLDS_KEY })
    onCopied(copy.id)
  }).finally(() => setMaking(false)) }
  return (
    <form className="new-world form-stack" aria-label={copyLabel(persona)} onSubmit={(event) => { event.preventDefault(); void make() }}
      onKeyDown={(event) => { if (event.key === 'Escape' && !making) onDone() }}>
      <div>
        <p className="new-world-title">{copyLabel(persona)}</p>
        <p className="subtle">{copyNote(persona)}</p>
      </div>
      <CityPick value={city} currentId={cityId} disabled={making} autoFocus onChange={setCity} />
      <div className="form-actions wrap">
        <button type="submit" className="button primary" disabled={making}>{making ? 'Making the copy…' : 'Make the copy'}</button>
        <button type="button" className="text-button" disabled={making} onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function PersonaRow({ persona, tag, onSwitchPersona, onDelete }: { persona: Persona; tag: string; onSwitchPersona: () => void; onDelete?: () => void }) {
  const name = personaName(persona)
  const suffix = personaSuffix(persona.active, tag)
  return (
    <div className="persona-row">
      <span className="portrait persona-initial" aria-hidden="true">{initial(persona) || <UserRound size={18} />}</span>
      <h2 tabIndex={-1}>{personaTitle(persona)}{suffix && <span className="subtle"> ({suffix})</span>}</h2>
      {persona.active && !name && <button type="button" className="text-button" onClick={addName}>Add a name</button>}
      {!persona.active && <button type="button" className="button" onClick={onSwitchPersona}>{name ? `Be ${name}` : 'Switch to this persona'}</button>}
      {onDelete && <button type="button" className="text-button" onClick={onDelete}><Trash2 aria-hidden="true" />Delete</button>}
    </div>
  )
}

function WorldRow({ world, run, store, onSwitch }: { world: World; run: Run; store: (data: WorldsData) => void; onSwitch: () => void }) {
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(world.name)
  const [deleting, setDeleting] = useState(false)
  const rename = () => run(async () => { store(await api<WorldsData>(`/worlds/${world.id}`, { name }, 'PATCH')); setRenaming(false) })
  return (
    <li className="world-row" aria-current={world.active ? 'true' : undefined}>
      <span className="portrait" aria-hidden="true"><Globe /></span>
      {renaming
        ? <form className="world-rename" onSubmit={(event) => { event.preventDefault(); void rename() }}>
            <label className="visually-hidden" htmlFor={`world-name-${world.id}`}>World name</label>
            <input autoComplete="off" id={`world-name-${world.id}`} value={name} maxLength={80} required onChange={(event) => setName(event.target.value)} />
            <button type="submit" className="button">Save</button>
            <button type="button" className="text-button" onClick={() => { setRenaming(false); setName(world.name) }}>Cancel</button>
          </form>
        : <WorldText world={world} />}
      <span className="world-row-actions">
        <HereOrGo world={world} run={run} onSwitch={onSwitch} />
        {!renaming && <button type="button" className="text-button" onClick={() => setRenaming(true)}>Rename</button>}
        {!world.active && !world.first && <button type="button" className="text-button" aria-label={`Delete ${world.name}`} onClick={() => setDeleting(true)}><Trash2 aria-hidden="true" /></button>}
      </span>
      {world.active && <JustWatch world={world} run={run} />}
      {deleting && <ConfirmDialog title={`Delete ${world.name}?`} onClose={() => setDeleting(false)} actions={<>
        <button type="button" className="button" onClick={() => setDeleting(false)}>Keep it</button>
        <button type="button" className="button danger" onClick={() => void run(async () => { store(await api<WorldsData>(`/worlds/${world.id}`, undefined, 'DELETE')); setDeleting(false) })}>Delete</button>
      </>}>
        <p>{companionsLine(world)} and everything that happened there go with it. A backup is kept in the data folder, under backups/deleted-worlds.</p>
      </ConfirmDialog>}
    </li>
  )
}

/** "You are here", with Resume when this world is paused in Settings > Pause (Iris, 2026-10-31); or Go there. */
function HereOrGo({ world, run, onSwitch }: { world: World; run: Run; onSwitch: () => void }) {
  const client = useQueryClient()
  if (!world.active) return <button type="button" className="button" onClick={onSwitch}>Go there</button>
  const resume = () => run(async () => { await api('/resume', {}); await client.invalidateQueries() })
  return <>
    <span className="subtle">You are here</span>
    {world.paused_in_settings && <button type="button" className="text-button" onClick={() => void resume()}>Resume</button>}
  </>
}

/** A world's name and badges, its companions, and since when life has stood still there if it has (worldsText
 * `pausedNote`): only the world the user is in runs. */
function WorldText({ world }: { world: World }) {
  const note = pausedNote(world, new Date())
  return (
    <span className="world-row-text">
      <span className="world-row-name"><strong>{world.name}</strong><YearBadge world={world} />{world.paused && <span className="badge paused-badge"><Pause aria-hidden="true" />Paused</span>}</span>
      <span className="subtle">{companionsLine(world)}{world.watching ? ' · Just watching' : ''}</span>
      {note && <span className="subtle paused-note">{note}</span>}
    </span>
  )
}

/** The year it is in a world that runs in the past (Back when, or started in a past year). */
function YearBadge({ world }: { world: World }) {
  const badge = yearBadge(world)
  if (!badge) return null
  return <span className="badge year-badge" title={badge.label}><History aria-hidden="true" /><span className="visually-hidden">{badge.label}</span><span aria-hidden="true">{badge.text}</span></span>
}

/** "Just watch" (companion/observer.py) for the world the user is in: their persona sits out while everyone else's
 * life goes on, and the Watching page opens. */
function JustWatch({ world, run }: { world: World; run: Run }) {
  const { change } = useWatchActions()
  const toggle = (on: boolean) => run(async () => {
    await change({ watching: on })
    if (on) window.location.hash = '#watch'
  })
  return (
    <div className="world-watch">
      <Toggle label="Just watch" checked={!!world.watching} onChange={(on) => void toggle(on)}
        hint="Sit back and watch this world go on without you. Nobody texts you or asks you along meanwhile. Writing to anyone steps you back in." />
    </div>
  )
}
