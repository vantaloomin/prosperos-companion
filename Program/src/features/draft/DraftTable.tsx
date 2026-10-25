import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Dices, Download, FilePlus2, LoaderCircle, Save, Upload, XCircle } from 'lucide-react'
import { api, ApiError } from '../../api'
import { Notice } from '../../components/Feedback'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { TextArea, TextInput } from '../../components/Fields'
import { SketchMap } from '../map/SketchMap'
import { definitionOf, exportName, groupNotes, parseDefinition, type CityListing } from '../world/cityText'
import { isWorldMap } from '../world/worldMap'
import { ColourList, EventList, HoodList, PlaceList, TransitList, WorkList, type ListProps } from './DraftLists'
import {
  addHood, addPlace, briefLine, CITIES_CHANNEL, changeCity, changeItem, EXAMPLES, inHood, keepWork, loadWork, mapData, newSeed, redrawsAll,
  removeItem, takeSection, uniqueId, type Checked, type Definition, type Drafted, type Item, type ListKey, type Rolls, type Section, type Work,
} from './draftText'

type Tab = 'map' | 'overview' | 'hoods' | 'places' | 'work' | 'transit' | 'events' | 'colour' | 'check'
type CheckState = { state: 'checking' } | { state: 'done'; checked: Checked } | { state: 'failed'; message: string }
type Feedback = { tone: 'success' | 'error' | 'info'; text: string; saveAsNew?: boolean } | null
/** A step that would throw away the user's changes waits for a yes. */
type Asking = { title: string; text: string; yes: string; go: () => void } | null

const message = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/**
 * Prospero's Draft Table: one line in, a whole place out (companion/world/draft), drawn on a map with every part in
 * a list to change. Roll again redraws one part and keeps the user's changes elsewhere; the check panel says what
 * Companion would make of it; Save puts it with the user's own cities. Its own window, from the same server.
 */
export function DraftTable() {
  const [work, setWork] = useState<Work | null>(loadWork)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [asking, setAsking] = useState<Asking>(null)
  useEffect(() => keepWork(work), [work])

  const draw = async (line: string, seed: string, rolls: Rolls, section?: Section) => {
    setBusy(true)
    setError('')
    try {
      const made = await api<Drafted>('/world/draft', { line, seed, rolls })
      setWork((current) => current && section && !redrawsAll(section)
        ? { ...current, rolls, definition: takeSection(current.definition, made.definition, section) }
        : { line, seed, rolls, definition: made.definition, brief: made.brief, edited: false })
    } catch (failure) { setError(message(failure, 'The table could not draw that up. Try again.')) } finally { setBusy(false) }
  }
  // Anything that replaces the whole place asks first once the user has changed it.
  const careful = (go: () => void, title: string, yes: string) => {
    if (!work?.edited) { go(); return }
    setAsking({ title, yes, go, text: 'Your changes to this place are replaced. A place you saved stays in your cities.' })
  }

  return (
    <main id="main" tabIndex={-1} className="draft-page">
      {work ? <Table work={work} setWork={setWork} busy={busy} error={error} draw={draw} careful={careful} />
        : <Start busy={busy} error={error} onDraw={(line) => void draw(line, newSeed(), {})} onOpen={(opened) => setWork(opened)} onError={setError} />}
      {asking && <ConfirmDialog title={asking.title} onClose={() => setAsking(null)} actions={<>
        <button type="button" className="button" onClick={() => setAsking(null)}>Cancel</button>
        <button type="button" className="button primary" onClick={() => { setAsking(null); asking.go() }}>{asking.yes}</button>
      </>}><p>{asking.text}</p></ConfirmDialog>}
    </main>
  )
}

/** The empty table: a line, or nothing at all for a surprise. */
function Start({ busy, error, onDraw, onOpen, onError }: { busy: boolean; error: string; onDraw: (line: string) => void; onOpen: (work: Work) => void; onError: (text: string) => void }) {
  const [line, setLine] = useState('')
  const submit = (event: FormEvent) => { event.preventDefault(); if (!busy) onDraw(line) }
  return (
    <div className="draft-start">
      <h1>Prospero's Draft Table</h1>
      <p className="draft-lede">Describe a place in a line. The table draws up the rest: its neighborhoods, places, work, getting about, yearly events, local color and weather. Change anything you like after.</p>
      <form className="draft-line" onSubmit={submit}>
        <label htmlFor="draft-line">Your place, in a line</label>
        <div className="draft-line-row">
          <input id="draft-line" value={line} maxLength={400} placeholder={`For example: ${EXAMPLES[0]}`} onChange={(event) => setLine(event.target.value)} />
          <button type="submit" className="button primary" aria-disabled={busy}>{busy ? <LoaderCircle aria-hidden="true" className="spin" /> : <FilePlus2 aria-hidden="true" />}Draw it up</button>
        </div>
        <div className="draft-examples">
          <span className="subtle">Or try</span>
          {EXAMPLES.slice(1).map((example) => <button key={example} type="button" className="vibe-pick" disabled={busy} onClick={() => { setLine(example); onDraw(example) }}>{example}</button>)}
          <button type="button" className="vibe-pick" disabled={busy} onClick={() => onDraw('')}><Dices aria-hidden="true" />Surprise me</button>
        </div>
      </form>
      <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
      <OpenFile className="text-button" onOpen={onOpen} onError={onError} />
      <p className="subtle">Places are saved with your own cities in Companion, on this computer. Nothing here uses a model.</p>
    </div>
  )
}

/** A city file someone made or shared, opened to change. It has no line, so nothing on it rolls again. */
function OpenFile({ className, onOpen, onError }: { className: string; onOpen: (work: Work) => void; onError: (text: string) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const open = async (file: File | undefined) => {
    if (input.current) input.current.value = ''
    if (!file) return
    const text = await file.text()
    if (isWorldMap(file.name, text.slice(0, 4096))) { onError('That is a Marinara world map. Open it in Companion under Settings > Cities, which turns it into a city.'); return }
    const parsed = parseDefinition(text)
    if (!parsed.ok) { onError(parsed.error); return }
    const definition = definitionOf(parsed.value) as Partial<Definition>
    if (!Array.isArray(definition.neighborhoods) || !Array.isArray(definition.places)) { onError('That file is not a city file: it has no neighborhoods or places.'); return }
    onOpen({ line: '', seed: '', rolls: {}, definition: { employers: [], career_hubs: [], transit: [], annual_events: [], local_color: [], ...definition } as Definition, brief: null, edited: false })
  }
  return <>
    <button type="button" className={className} onClick={() => input.current?.click()}><Upload aria-hidden="true" />Open a city file</button>
    <input ref={input} type="file" accept=".json,application/json" hidden onChange={(event) => void open(event.target.files?.[0])} />
  </>
}

interface TableProps {
  work: Work; setWork: (change: (work: Work | null) => Work | null) => void; busy: boolean; error: string
  draw: (line: string, seed: string, rolls: Rolls, section?: Section) => Promise<void>
  careful: (go: () => void, title: string, yes: string) => void
}

/** The drawn-up place: the map beside the lists, or a tab of its own on a phone. */
function Table({ work, setWork, busy, error, draw, careful }: TableProps) {
  const [tab, setTab] = useState<Tab>('overview')
  const [open, setOpen] = useState<string | null>(null)
  const [removing, setRemoving] = useState<{ key: ListKey; item: Item } | null>(null)
  const check = useCheck(work.definition)
  const edit = (change: (definition: Definition) => Definition) => setWork((current) => current && { ...current, definition: change(current.definition), edited: true })
  const roll = (section: Section) => {
    const rolls = { ...work.rolls, [section]: (work.rolls[section] ?? 0) + 1 }
    const go = () => void draw(work.line, work.seed, rolls, section)
    if (redrawsAll(section)) careful(go, 'Draw the whole place again?', 'Draw it again')
    else go()
  }
  const remove = (key: ListKey, item: Item) => {
    if (key === 'neighborhoods') { setRemoving({ key, item }); return }
    edit((definition) => removeItem(definition, key, item.id))
  }
  const list: ListProps = {
    definition: work.definition, open, onOpen: setOpen, onRemove: remove, onRoll: work.brief ? roll : undefined,
    onChange: (key, id, change) => edit((definition) => changeItem(definition, key, id, change)),
  }
  const pick = (id: string) => { setTab('places'); setOpen(id) }
  const add = (made: { definition: Definition; id: string }, to: Tab) => { edit(() => made.definition); setTab(to); setOpen(made.id) }
  // On a phone the map is a tab; beside it on a wider screen, the overview shows instead.
  const overview = <Overview work={work} busy={busy} setWork={setWork} draw={draw} careful={careful} onRoll={roll} />
  return (
    <div className="draft-table">
      <TableBar work={work} setWork={setWork} check={check} onCheck={() => setTab('check')} careful={careful} />
      <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
      <div className={`draft-body${busy ? ' busy' : ''}`} data-tab={tab} aria-busy={busy}>
        <DraftMap definition={work.definition} selected={open} onSelect={pick} />
        <section className="draft-panel" aria-label="The place, part by part">
          <Tabs tab={tab} onTab={(next) => { setTab(next); setOpen(null) }} definition={work.definition} check={check} />
          <div className="draft-panel-body" role="tabpanel" id="draft-tabpanel" aria-labelledby={`draft-tab-${tab === 'map' ? 'overview' : tab}`}>
            {{
              map: () => overview, overview: () => overview, check: () => <CheckPanel check={check} />,
              hoods: () => <HoodList {...list} onAdd={() => add(addHood(work.definition), 'hoods')} />,
              places: () => <PlaceList {...list} onAdd={(hood) => add(addPlace(work.definition, hood), 'places')} />,
              work: () => <WorkList {...list} />, transit: () => <TransitList {...list} />, events: () => <EventList {...list} />, colour: () => <ColourList {...list} />,
            }[tab]()}
          </div>
        </section>
      </div>
      {removing && <RemoveHood definition={work.definition} hood={removing.item} onClose={() => setRemoving(null)}
        onRemove={() => { edit((definition) => removeItem(definition, 'neighborhoods', removing.item.id)); setRemoving(null) }} />}
    </div>
  )
}

function RemoveHood({ definition, hood, onClose, onRemove }: { definition: Definition; hood: Item; onClose: () => void; onRemove: () => void }) {
  const { places, employers } = inHood(definition, hood.id)
  const goes = [places && `${places} ${places === 1 ? 'place' : 'places'}`, employers && `${employers} ${employers === 1 ? 'employer' : 'employers'}`].filter(Boolean).join(' and ')
  return (
    <ConfirmDialog title={`Remove ${hood.name}?`} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button danger" onClick={onRemove}>Remove</button>
    </>}><p>{goes ? `Its ${goes} go with it.` : 'Nothing else is in it.'} Events held there move to all over {definition.enclosed ? 'the ship' : 'town'}.</p></ConfirmDialog>
  )
}

/** Checks the place the way Companion loads a city, a moment after the last change. */
function useCheck(definition: Definition): CheckState {
  const [result, setResult] = useState<CheckState>({ state: 'checking' })
  useEffect(() => {
    let live = true
    const timer = window.setTimeout(() => {
      api<Checked>('/world/draft/check', definition)
        .then((checked) => { if (live) setResult({ state: 'done', checked }) })
        .catch((failure) => { if (live) setResult({ state: 'failed', message: message(failure, 'It could not be checked.') }) })
    }, 450)
    return () => { live = false; window.clearTimeout(timer) }
  }, [definition])
  return result
}

/** The map is drawn again only when what it shows changes, not on every letter of a summary. */
function DraftMap({ definition, selected, onSelect }: { definition: Definition; selected: string | null; onSelect: (id: string) => void }) {
  const shape = JSON.stringify([definition.name, definition.water, definition.neighborhoods.map((hood) => [hood.id, hood.name, hood.lat, hood.lon]),
    definition.places.map((item) => [item.id, item.name, item.kind, item.neighborhood])])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `shape` is everything the map draws.
  const data = useMemo(() => mapData(definition), [shape])
  const parts = definition.enclosed ? 'Decks' : 'Neighborhoods'
  return (
    <section className="draft-map" aria-label={`Map of ${definition.name}`}>
      <SketchMap fit data={data} selected={data.places.some((item) => item.id === selected) ? selected : null} onSelect={onSelect}
        caption={`Drawn map. ${parts} are placed by how they connect, not to scale. Pick a place to change it.`} />
    </section>
  )
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'map', label: 'Map' }, { id: 'overview', label: 'Overview' }, { id: 'hoods', label: 'Neighborhoods' }, { id: 'places', label: 'Places' },
  { id: 'work', label: 'Work' }, { id: 'transit', label: 'Getting about' }, { id: 'events', label: 'Events' }, { id: 'colour', label: 'Local color' }, { id: 'check', label: 'Check' },
]

function count(tab: Tab, definition: Definition): number | null {
  const lists: Partial<Record<Tab, unknown[]>> = { hoods: definition.neighborhoods, places: definition.places, work: definition.employers, transit: definition.transit, events: definition.annual_events, colour: definition.local_color }
  return lists[tab]?.length ?? null
}

/** The parts as tabs, scrolling sideways on a phone, where the map is a tab of its own. */
function Tabs({ tab, onTab, definition, check }: { tab: Tab; onTab: (tab: Tab) => void; definition: Definition; check: CheckState }) {
  // A tab picked from elsewhere (a place on the map) scrolls into the strip on a phone.
  useEffect(() => { document.getElementById(`draft-tab-${tab}`)?.scrollIntoView({ block: 'nearest', inline: 'nearest' }) }, [tab])
  const move = (event: KeyboardEvent, index: number) => {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    const next = TABS[(index + step + TABS.length) % TABS.length]
    onTab(next.id)
    document.getElementById(`draft-tab-${next.id}`)?.focus()
  }
  return (
    <div className="draft-tabs" role="tablist" aria-label="Parts of the place">
      {TABS.map((item, index) => {
        const number = count(item.id, definition)
        const label = item.id === 'hoods' && definition.enclosed ? 'Decks' : item.label
        return (
          <button key={item.id} id={`draft-tab-${item.id}`} type="button" role="tab" className={`draft-tab draft-tab-${item.id}`} aria-selected={tab === item.id}
            aria-controls="draft-tabpanel" tabIndex={tab === item.id ? 0 : -1} onClick={() => onTab(item.id)} onKeyDown={(event) => move(event, index)}>
            {label}{number !== null && <span className="subtle"> {number}</span>}{item.id === 'check' && <CheckMark check={check} />}
          </button>
        )
      })}
    </div>
  )
}

function CheckMark({ check }: { check: CheckState }) {
  const state = checkState(check)
  if (state === 'ready') return <CheckCircle2 aria-label="ready" className="draft-check-ok" />
  if (state === 'checking') return null
  return <AlertTriangle aria-label="something to look at" className="draft-check-warn" />
}

function checkState(check: CheckState): 'checking' | 'ready' | 'thin' | 'broken' {
  if (check.state === 'checking') return 'checking'
  if (check.state === 'failed') return 'broken'
  return check.checked.warnings.length ? 'thin' : 'ready'
}

/** The name of the place, what it says on its tin, and Save. */
function TableBar({ work, setWork, check, onCheck, careful }: { work: Work; setWork: TableProps['setWork']; check: CheckState; onCheck: () => void; careful: TableProps['careful'] }) {
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [saving, setSaving] = useState(false)
  const save = async (asNew: boolean) => {
    setSaving(true)
    setFeedback(null)
    try {
      const definition = asNew ? { ...work.definition, id: uniqueId(work.definition.name, (await api<CityListing[]>('/world/cities')).map((city) => city.id)) } : work.definition
      const saved = work.saved && !asNew
        ? await api<CityListing & { revision: number }>(`/world/cities/${work.saved.id}`, { definition, expected_revision: work.saved.revision }, 'PUT')
        : await api<CityListing & { revision: number }>('/world/cities', definition)
      setWork((current) => current && { ...current, definition: { ...current.definition, id: saved.id }, saved: { id: saved.id, revision: saved.revision } })
      setFeedback({ tone: 'success', text: `Saved ${saved.name}. It is in Companion now, under Custom in Settings > Cities.` })
      announceSaved()
    } catch (failure) {
      setFeedback({ tone: 'error', text: message(failure, 'Not saved.'), saveAsNew: failure instanceof ApiError && failure.status === 409 })
    } finally { setSaving(false) }
  }
  const broken = check.state === 'failed'
  return (
    <header className="draft-bar">
      <div className="draft-title">
        <p className="draft-brand">Prospero's Draft Table</p>
        <h1>{work.definition.name || 'Unnamed place'}</h1>
        <p className="subtle">{briefLine(work.brief, work.definition)}</p>
      </div>
      <CheckChip check={check} onClick={onCheck} />
      <div className="draft-bar-actions">
        <button type="button" className="button primary" disabled={saving || broken} onClick={() => void save(false)}><Save aria-hidden="true" />{work.saved ? 'Save changes' : 'Save to my cities'}</button>
        <button type="button" className="button" aria-label="Save as file" title="Save as file" onClick={() => saveFile(work.definition)}><Download aria-hidden="true" /><span className="draft-bar-label">Save as file</span></button>
        <button type="button" className="button" aria-label="New place" title="New place" onClick={() => careful(() => setWork(() => null), 'Start a new place?', 'Start again')}><FilePlus2 aria-hidden="true" /><span className="draft-bar-label">New place</span></button>
      </div>
      <div className="draft-bar-feedback" aria-live="polite">{feedback && <Notice tone={feedback.tone} action={feedback.saveAsNew ? <button type="button" className="text-button notice-link" onClick={() => void save(true)}>Save as a new city</button> : undefined}>{feedback.text}</Notice>}</div>
    </header>
  )
}

function CheckChip({ check, onClick }: { check: CheckState; onClick: () => void }) {
  const state = checkState(check)
  const warnings = check.state === 'done' ? check.checked.warnings.length : 0
  const text = { checking: 'Checking…', ready: 'Ready', thin: `${warnings} to look at`, broken: 'Will not load yet' }[state]
  const Icon = { checking: LoaderCircle, ready: CheckCircle2, thin: AlertTriangle, broken: XCircle }[state]
  return <button type="button" className={`draft-chip draft-chip-${state}`} onClick={onClick}><Icon aria-hidden="true" />{text}</button>
}

/** Companion's own window, if open, lists the city straight away (features/world/Cities.tsx). */
function announceSaved() {
  try { const channel = new BroadcastChannel(CITIES_CHANNEL); channel.postMessage('saved'); channel.close() } catch { /* it lists it on its next look */ }
}

function saveFile(definition: Definition) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([JSON.stringify(definition, null, 1)], { type: 'application/json' }))
  link.download = exportName(definition.id)
  link.click()
  URL.revokeObjectURL(link.href)
}

/** The line it was drawn from, another take on it, and the place's own name and summary. */
function Overview({ work, busy, setWork, draw, careful, onRoll }: Pick<TableProps, 'work' | 'busy' | 'setWork' | 'draw' | 'careful'> & { onRoll: (section: Section) => void }) {
  const [line, setLine] = useState(work.line)
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CityListing[]>('/world/cities') })
  const anchor = work.brief && cities.data?.find((city) => city.id === work.brief?.anchor)
  const change = (patch: Parameters<typeof changeCity>[1]) => setWork((current) => current && { ...current, definition: changeCity(current, patch), edited: true })
  const redraw = (event: FormEvent) => {
    event.preventDefault()
    if (!busy) careful(() => void draw(line, newSeed(), {}), 'Draw up a new place?', 'Draw it up')
  }
  return (
    <section className="draft-list form-stack" aria-labelledby="draft-overview">
      <h2 id="draft-overview" className="visually-hidden">Overview</h2>
      <form className="draft-line" onSubmit={redraw}>
        <label htmlFor="draft-line-again">{work.brief ? 'Drawn from' : 'Draw up a new place'}</label>
        <div className="draft-line-row">
          <input id="draft-line-again" value={line} maxLength={400} placeholder={EXAMPLES[0]} onChange={(event) => setLine(event.target.value)} />
          <button type="submit" className="button" aria-disabled={busy}><FilePlus2 aria-hidden="true" />Draw it up</button>
        </div>
        {work.brief && <div className="form-actions wrap">
          <button type="button" className="button" disabled={busy} onClick={() => careful(() => void draw(work.line, newSeed(), {}), 'Take another go at this line?', 'Another take')}><Dices aria-hidden="true" />Another take</button>
          <button type="button" className="button" disabled={busy} onClick={() => onRoll('name')}><Dices aria-hidden="true" />Another name</button>
        </div>}
      </form>
      {!work.brief && <p className="subtle">Opened from a file. Roll again needs the line a place was drawn from, so it is off for this one.</p>}
      <TextInput label="Name" value={work.definition.name} maxLength={120} onChange={(name) => change({ name })} hint={work.saved ? 'Saved with your cities, so its id stays as it is.' : undefined} />
      <TextArea label="What it is like" value={work.definition.summary} maxLength={400} rows={3} onChange={(summary) => change({ summary })} />
      <div className="draft-pair">
        <TextInput label="Region" value={work.definition.region} maxLength={120} onChange={(region) => change({ region })} />
        <TextInput label={work.definition.enclosed ? 'Kind of ship' : 'Country or realm'} value={work.definition.country} maxLength={120} onChange={(country) => change({ country })} />
      </div>
      {anchor && <p className="subtle">Money, prices, holidays and names follow {anchor.name}, which ships with Companion, so a day here costs what a day there does.</p>}
    </section>
  )
}

/** What Companion would make of the place if it were saved now. */
function CheckPanel({ check }: { check: CheckState }) {
  if (check.state === 'checking') return <p className="subtle draft-checking"><LoaderCircle aria-hidden="true" className="spin" />Checking…</p>
  if (check.state === 'failed') return <section className="draft-list form-stack" aria-labelledby="draft-check"><h2 id="draft-check">Check</h2><Notice tone="error">Companion would not load this yet. {check.message}</Notice></section>
  const { warnings, notes, summary } = check.checked
  const counts = summary.counts
  return (
    <section className="draft-list form-stack" aria-labelledby="draft-check">
      <h2 id="draft-check">Check</h2>
      {!warnings.length && !notes.length && <Notice tone="success">Ready. Companion loads it as it is, with nothing to fix.</Notice>}
      {warnings.map((warning) => <Notice key={warning} tone="warning">{warning} Days there repeat sooner.</Notice>)}
      {notes.length > 0 && <div><p>Companion tidies these on the way in:</p><ul className="city-notes">{groupNotes(notes).map((note) => <li key={note}>{note}</li>)}</ul></div>}
      <p className="subtle">{counts.neighborhoods} {summary.enclosed ? 'decks' : 'neighborhoods'}, {counts.places} places, {counts.employers} employers, {counts.annual_events} yearly events.</p>
    </section>
  )
}
