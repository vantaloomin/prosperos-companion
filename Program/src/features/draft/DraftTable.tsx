import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Dices, Download, ExternalLink, FilePlus2, LoaderCircle, Pencil, Plus, Save, Undo2, Upload, X, XCircle } from 'lucide-react'
import { api, ApiError } from '../../api'
import { Notice } from '../../components/Feedback'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { SketchMap } from '../map/SketchMap'
import { definitionOf, exportName, groupNotes, parseDefinition, type CityListing } from '../world/cityText'
import { isWorldMap, readWorldMap } from '../world/worldMap'
import { Choice, ColourList, EventList, HoodList, ItemRow, PlaceList, TransitList, WorkList, type ListProps } from './DraftLists'
import { PolishContext, type Polishing } from './polishContext'
import {
  addHood, addPlace, briefLine, changeNeighbour, CITIES_CHANNEL, PLACE_KINDS, changeCity, changeItem, EXAMPLES, inHood, journey, JOURNEY_HOURS, keepWork, loadWork, mapData, newSeed,
  plural, POLISHED, redrawsAll, removeItem, settle, SHOW_CITY_KEY, staleNames, keptRows, takePolish, takeSection, touch, uniqueId, weatherOf, withWeather, type Checked, type Definition, type Drafted, type Item, type ListKey, type Neighbour, type Rolls, type Section, type Weather, type Work,
} from './draftText'

type Tab = 'map' | 'overview' | 'hoods' | 'places' | 'work' | 'transit' | 'events' | 'colour' | 'check'
type CheckState = { state: 'checking' } | { state: 'done'; checked: Checked } | { state: 'failed'; message: string }
type Feedback = { tone: 'success' | 'error'; text: string; saveAsNew?: boolean; undo?: () => void; show?: string } | null
/** A step that would throw away the user's changes waits for a yes. */
type Undoable = { section: Section; before: Work; after: Definition }
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
          <input autoComplete="off" id="draft-line" value={line} maxLength={400} placeholder="e.g. a cold fishing town, 1920s" onChange={(event) => setLine(event.target.value)} />
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
      <p className="subtle">Places are saved with your own cities in Companion, on this computer. Nothing here uses a model unless you press Polish.</p>
    </div>
  )
}

/** A city file someone made or shared, opened to change. It has no line, so nothing on it rolls again. */
function OpenFile({ className, onOpen, onError }: { className: string; onOpen: (work: Work) => void; onError: (text: string) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const open = async (file: File | undefined) => {
    if (input.current) input.current.value = ''
    if (!file) return
    if (isWorldMap(file.name, await file.slice(0, 4096).text())) { await openWorldMap(file); return }
    const parsed = parseDefinition(await file.text())
    if (!parsed.ok) { onError(parsed.error); return }
    const definition = definitionOf(parsed.value) as Partial<Definition>
    if (!Array.isArray(definition.neighborhoods) || !Array.isArray(definition.places)) { onError('That file is not a city file: it has no neighborhoods or places.'); return }
    onOpen({ line: '', seed: '', rolls: {}, definition: { employers: [], career_hubs: [], transit: [], annual_events: [], local_color: [], ...definition } as Definition, brief: null, edited: false })
  }
  // A Marinara world map becomes a city file to change here (companion/world/marinara.py); its pictures stay behind.
  const openWorldMap = async (file: File) => {
    try {
      const made = await api<{ definition: Definition; notes: string[] }>('/world/draft/marinara', await readWorldMap(file))
      onOpen({ line: '', seed: '', rolls: {}, definition: { employers: [], career_hubs: [], transit: [], annual_events: [], local_color: [], ...(made.definition as Partial<Definition>) } as Definition, brief: null, edited: false, openedNotes: made.notes })
    } catch (failure) { onError(message(failure, 'That world map could not be opened.')) }
  }
  return <>
    <button type="button" className={className} onClick={() => input.current?.click()}><Upload aria-hidden="true" />Open a city file or world map</button>
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
  const [toast, setToast] = useState<Feedback>(null)
  const check = useCheck(work)
  useAutoGrow()
  const edit = (change: (definition: Definition) => Definition, removed?: string) => setWork((current) => current && settle(current, change(current.definition), removed))
  const roll = (section: Section) => {
    const rolls = { ...work.rolls, [section]: (work.rolls[section] ?? 0) + 1 }
    const go = () => void draw(work.line, work.seed, rolls, section)
    if (redrawsAll(section)) careful(go, 'Draw the whole place again?', 'Draw it again')
    else go()
  }
  const remove = (key: ListKey, item: Item) => {
    if (key === 'neighborhoods') { setRemoving({ key, item }); return }
    edit((definition) => removeItem(definition, key, item.id), key === 'places' ? undefined : item.name)
  }
  const list: ListProps = {
    definition: work.definition, open, onOpen: setOpen, onRemove: remove, onRoll: work.brief ? roll : undefined,
    onChange: (key, id, change) => setWork((current) => current && touch(settle(current, changeItem(current.definition, key, id, change)), id)),
  }
  // On a phone a picked place shows a card over the map first; beside the lists, its row opens straight away.
  const pick = (id: string) => { if (tab !== 'map') setTab('places'); setOpen(id) }
  const add = (made: { definition: Definition; id: string }, to: Tab) => { edit(() => made.definition); setTab(to); setOpen(made.id) }
  const polishValue = usePolish(work, setWork, setToast)
  // On a phone the map is a tab; beside it on a wider screen, the overview shows instead.
  const overview = <Overview work={work} busy={busy} setWork={setWork} draw={draw} careful={careful} onRoll={roll} />
  return (
    <div className="draft-table">
      <TableBar work={work} setWork={setWork} check={check} onCheck={() => setTab('check')} careful={careful} toast={toast} setToast={setToast} />
      <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
      <div className={`draft-body${busy ? ' busy' : ''}`} data-tab={tab} aria-busy={busy}>
        <DraftMap definition={work.definition} selected={open} onSelect={pick} mapTab={tab === 'map'} onEdit={() => setTab('places')} onClose={() => setOpen(null)} />
        <PolishContext.Provider value={polishValue}>
        <section className="draft-panel" aria-label="The place, part by part">
          <Tabs tab={tab} onTab={(next) => { setTab(next); setOpen(null) }} definition={work.definition} check={check} />
          <div className="draft-panel-body" role="tabpanel" id="draft-tabpanel" aria-labelledby={`draft-tab-${tab === 'map' ? 'overview' : tab}`}>
            {{
              map: () => overview, overview: () => overview, check: () => <CheckPanel check={check} opened={work.openedNotes} />,
              hoods: () => <HoodList {...list} onAdd={() => add(addHood(work.definition), 'hoods')} />,
              places: () => <PlaceList {...list} onAdd={(hood) => add(addPlace(work.definition, hood), 'places')} />,
              work: () => <WorkList {...list} />, transit: () => <TransitList {...list} />, events: () => <EventList {...list} />, colour: () => <ColourList {...list} />,
            }[tab]()}
          </div>
        </section>
        </PolishContext.Provider>
      </div>
      {removing && <RemoveHood definition={work.definition} hood={removing.item} onClose={() => setRemoving(null)}
        onRemove={() => { edit((definition) => removeItem(definition, 'neighborhoods', removing.item.id), removing.item.name); setRemoving(null) }} />}
    </div>
  )
}

/** Polish for the table's lists: the user's text model rewrites one list's names and summaries, and the last polish
 * can be undone until the next change. */
function usePolish(work: Work, setWork: TableProps['setWork'], setToast: (toast: Feedback) => void): Polishing {
  const [polishing, setPolishing] = useState<Section | null>(null)
  // The last polish, which can be undone until the next change.
  const [undo, setUndo] = useState<Undoable | null>(null)
  const latest = useRef(work)
  useEffect(() => { latest.current = work })
  const ready = useQuery({ queryKey: ['draft-polish-ready'], queryFn: () => api<{ ready: boolean }>('/world/draft/polish') })
  // The user's text model rewrites one list's names and summaries, leaving rows the user changed; Undo puts them back.
  const polish = async (section: Section) => {
    setPolishing(section)
    setToast(null)
    const asked = work
    try {
      const made = await api<{ definition: Definition; changed: number; ids: string[] }>('/world/draft/polish', { definition: asked.definition, section, line: asked.line, keep: asked.touched ?? [] })
      // Rows changed while the model was writing stay as the user left them.
      const before = latest.current
      const next = takePolish(before, section, made.definition, made.ids)
      if (next.definition === before.definition) { setToast({ tone: 'success', text: 'Your text model left them as they were.' }); return }
      setWork(() => next)
      setUndo({ section, before, after: next.definition })
      const changed = made.ids.filter((id) => !before.touched?.includes(id)).length
      const kept = keptRows(asked, section)
      setToast({ tone: 'success', text: `Polished ${changed} ${POLISHED[section]}.${kept ? ` ${kept === 1 ? 'The one' : `The ${kept}`} you changed ${kept === 1 ? 'was' : 'were'} left alone.` : ''}`, undo: () => takeBack({ section, before, after: next.definition }) })
    } catch (failure) { setToast({ tone: 'error', text: message(failure, 'They could not be polished. Try again.') }) } finally { setPolishing(null) }
  }
  const takeBack = (last: Undoable) => {
    setWork((current) => current && current.definition === last.after ? last.before : current)
    setUndo(null)
    setToast(null)
  }
  const undoable = undo && undo.after === work.definition ? undo : null
  return {
    polish: (section) => void polish(section), polishing, ready: ready.data?.ready ?? null,
    undoable: undoable?.section ?? null, undo: () => { if (undoable) takeBack(undoable) }, polished: new Set(work.polished ?? []),
  }
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
function useCheck(work: Work): CheckState {
  const definition = work.definition
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
  // A summary the user wrote that still names a part they removed is a thin spot of its own.
  const stale = staleNames(work).map((name) => `"What it is like" names ${name}, which is gone.`)
  return result.state === 'done' && stale.length ? { ...result, checked: { ...result.checked, warnings: [...stale, ...result.checked.warnings] } } : result
}

/** Text boxes grow with their text, where the browser cannot do it with CSS alone (field-sizing). */
function useAutoGrow() {
  useLayoutEffect(() => {
    if (typeof CSS !== 'undefined' && CSS.supports('field-sizing', 'content')) return
    const grow = (box: HTMLTextAreaElement) => { box.style.height = 'auto'; box.style.height = `${box.scrollHeight + 2}px` }
    document.querySelectorAll<HTMLTextAreaElement>('.draft-page textarea').forEach(grow)
    const typed = (event: Event) => { if (event.target instanceof HTMLTextAreaElement) grow(event.target) }
    document.addEventListener('input', typed)
    return () => document.removeEventListener('input', typed)
  })
}

/** The map is drawn again only when what it shows changes, not on every letter of a summary. */
interface MapProps { definition: Definition; selected: string | null; onSelect: (id: string) => void; mapTab: boolean; onEdit: () => void; onClose: () => void }

function DraftMap({ definition, selected, onSelect, mapTab, onEdit, onClose }: MapProps) {
  const shape = JSON.stringify([definition.name, definition.water, definition.neighborhoods.map((hood) => [hood.id, hood.name, hood.lat, hood.lon]),
    definition.places.map((item) => [item.id, item.name, item.kind, item.neighborhood])])
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `shape` is everything the map draws.
  const data = useMemo(() => mapData(definition), [shape])
  const parts = definition.enclosed ? 'Decks' : 'Neighborhoods'
  // The whole place fits again after it changes shape, and when the phone's Map tab opens.
  const refit = `${definition.neighborhoods.map((hood) => hood.id).join()}|${definition.places.length}|${mapTab}`
  return (
    <section className="draft-map" aria-label={`Map of ${definition.name}`}>
      <SketchMap zoomable refit={refit} data={data} selected={data.places.some((item) => item.id === selected) ? selected : null} onSelect={onSelect}
        caption={`Drawn map. ${parts} are placed by how they connect, not to scale. Pick a place to change it.`} />
      {mapTab && <PickedCard definition={definition} id={selected} onEdit={onEdit} onClose={onClose} />}
    </section>
  )
}

/** On a phone's Map tab: the picked place, and a way to its row. */
function PickedCard({ definition, id, onEdit, onClose }: { definition: Definition; id: string | null; onEdit: () => void; onClose: () => void }) {
  const place = definition.places.find((item) => item.id === id)
  if (!place) return null
  const hood = definition.neighborhoods.find((item) => item.id === place.neighborhood)
  return (
    <div className="draft-picked" role="region" aria-label={place.name}>
      <div className="draft-picked-text">
        <p className="draft-picked-name">{place.name}</p>
        <p className="subtle">{[PLACE_KINDS[place.kind ?? ''] ?? place.kind, hood?.name].filter(Boolean).join(' · ')}</p>
      </div>
      <button type="button" className="button primary" onClick={onEdit}><Pencil aria-hidden="true" />Change it</button>
      <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
    </div>
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
  const strip = useRef<HTMLDivElement>(null)
  const [more, setMore] = useState({ left: false, right: false })
  // The row scrolls sideways, fading at an edge with more beyond it; the chosen tab always scrolls into view.
  useEffect(() => {
    const row = strip.current
    if (!row) return
    const edges = () => setMore({ left: row.scrollLeft > 2, right: row.scrollLeft + row.clientWidth < row.scrollWidth - 2 })
    document.getElementById(`draft-tab-${tab}`)?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    edges()
    row.addEventListener('scroll', edges, { passive: true })
    window.addEventListener('resize', edges)
    return () => { row.removeEventListener('scroll', edges); window.removeEventListener('resize', edges) }
  }, [tab])
  const move = (event: KeyboardEvent, index: number) => {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    // The Map tab is only there on a phone.
    const shown = TABS.filter((item) => document.getElementById(`draft-tab-${item.id}`)?.offsetParent)
    const at = Math.max(0, shown.findIndex((item) => item.id === TABS[index].id))
    const next = shown[(at + step + shown.length) % shown.length]
    onTab(next.id)
    document.getElementById(`draft-tab-${next.id}`)?.focus()
  }
  return (
    <div ref={strip} className={`draft-tabs${more.left ? ' more-left' : ''}${more.right ? ' more-right' : ''}`} role="tablist" aria-label="Parts of the place">
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
interface BarProps { work: Work; setWork: TableProps['setWork']; check: CheckState; onCheck: () => void; careful: TableProps['careful']; toast: Feedback; setToast: (toast: Feedback) => void }

function TableBar({ work, setWork, check, onCheck, careful, toast, setToast }: BarProps) {
  const weather = weatherOf(useWeathers(), work.definition)
  const [saving, setSaving] = useState(false)
  // The draft as last saved: Save rests as "Saved" until something changes.
  const [savedAs, setSavedAs] = useState<Definition | null>(null)
  const save = async (asNew: boolean) => {
    setSaving(true)
    setToast(null)
    try {
      const definition = asNew ? { ...work.definition, id: uniqueId(work.definition.name, (await api<CityListing[]>('/world/cities')).map((city) => city.id)) } : work.definition
      const saved = work.saved && !asNew
        ? await api<CityListing & { revision: number }>(`/world/cities/${work.saved.id}`, { definition, expected_revision: work.saved.revision }, 'PUT')
        : await api<CityListing & { revision: number }>('/world/cities', definition)
      const kept = { ...definition, id: saved.id }
      setWork((current) => current && { ...current, definition: kept, saved: { id: saved.id, revision: saved.revision }, polished: [] })
      setSavedAs(kept)
      setToast({ tone: 'success', text: `Saved ${saved.name}. It is in Companion now, under Custom in Settings > Life & cities.`, show: saved.id })
      announceSaved()
    } catch (failure) {
      setToast({ tone: 'error', text: message(failure, 'Not saved.'), saveAsNew: failure instanceof ApiError && failure.status === 409 })
    } finally { setSaving(false) }
  }
  const unchanged = savedAs === work.definition
  return (
    <header className="draft-bar">
      <div className="draft-title">
        <p className="draft-brand">Prospero's Draft Table</p>
        <h1>{work.definition.name || 'Unnamed place'}</h1>
        <p className="subtle">{briefLine(work.brief, work.definition, weather?.name)}</p>
      </div>
      <CheckChip check={check} onClick={onCheck} />
      <div className="draft-bar-actions">
        <button type="button" className="button primary" disabled={saving || unchanged || check.state === 'failed'} onClick={() => void save(false)}>
          {unchanged ? <CheckCircle2 aria-hidden="true" /> : <Save aria-hidden="true" />}{unchanged ? 'Saved' : work.saved ? 'Save changes' : 'Save to my cities'}
        </button>
        <button type="button" className="button" aria-label="Save as file" title="Save as file" onClick={() => saveFile(work.definition)}><Download aria-hidden="true" /><span className="draft-bar-label">Save as file</span></button>
        <button type="button" className="button" aria-label="New place" title="New place" onClick={() => careful(() => setWork(() => null), 'Start a new place?', 'Start again')}><FilePlus2 aria-hidden="true" /><span className="draft-bar-label">New place</span></button>
      </div>
      <Toast toast={toast} onClose={() => setToast(null)} onSaveAsNew={() => void save(true)} />
    </header>
  )
}

/** A note over the bottom of the window that moves nothing: a save goes after a few seconds, a problem stays. */
function Toast({ toast, onClose, onSaveAsNew }: { toast: Feedback; onClose: () => void; onSaveAsNew: () => void }) {
  useEffect(() => {
    if (toast?.tone !== 'success') return
    // Long enough to reach Undo or Show in Companion.
    const timer = window.setTimeout(onClose, toast.undo || toast.show ? 10000 : 5000)
    return () => window.clearTimeout(timer)
  }, [toast, onClose])
  return (
    <div className="draft-toast-area" aria-live="polite">
      {toast && <div className={`draft-toast draft-toast-${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}>
        {toast.tone === 'error' ? <XCircle aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
        <span>{toast.text}</span>
        {toast.saveAsNew && <button type="button" className="text-button draft-toast-action" onClick={onSaveAsNew}>Save as a new city</button>}
        {toast.undo && <button type="button" className="text-button draft-toast-action" onClick={toast.undo}><Undo2 aria-hidden="true" />Undo</button>}
        {toast.show && <button type="button" className="text-button draft-toast-action" onClick={() => showInCompanion(toast.show ?? '')}><ExternalLink aria-hidden="true" />Show in Companion</button>}
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
      </div>}
    </div>
  )
}

/** Ready, or how many things to fix: a status that opens the Check tab, not a button to press. */
function CheckChip({ check, onClick }: { check: CheckState; onClick: () => void }) {
  const state = checkState(check)
  const warnings = check.state === 'done' ? check.checked.warnings.length : 0
  const text = { checking: 'Checking…', ready: 'Ready', thin: `${warnings} to fix`, broken: 'Will not load yet' }[state]
  const Icon = { checking: LoaderCircle, ready: CheckCircle2, thin: AlertTriangle, broken: XCircle }[state]
  return <button type="button" className={`draft-chip draft-chip-${state}`} aria-label={`${text}. Open Check`} onClick={onClick}><Icon aria-hidden="true" />{text}</button>
}

/** Companion's own window, if open, lists the city straight away (features/world/Cities.tsx). */
function announceSaved() {
  try { const channel = new BroadcastChannel(CITIES_CHANNEL); channel.postMessage('saved'); channel.close() } catch { /* it lists it on its next look */ }
}

/** Companion's window opens Settings > Life & cities at the saved city: the open window if there is one, else a new one. */
function showInCompanion(id: string) {
  try { localStorage.setItem(SHOW_CITY_KEY, id) } catch { /* it opens on Settings > Life & cities all the same */ }
  try { const channel = new BroadcastChannel(CITIES_CHANNEL); channel.postMessage({ show: id }); channel.close() } catch { /* the new window reads it */ }
  const companion = window.opener as Window | null
  if (companion && !companion.closed) companion.focus()
  else window.open('/#settings/life', 'prospero-companion')
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
  // Typing in the summary keeps it as written; otherwise it follows the name and the parts of town.
  const change = (patch: Parameters<typeof changeCity>[1]) => setWork((current) => current && settle({ ...current, summaryEdited: current.summaryEdited || patch.summary !== undefined }, changeCity(current, patch)))
  const rewrite = () => setWork((current) => current && settle({ ...current, summaryEdited: false }, current.definition))
  const redraw = (event: FormEvent) => {
    event.preventDefault()
    if (!busy) careful(() => void draw(line, newSeed(), {}), 'Draw up a new place?', 'Draw it up')
  }
  // An opened file has no line to draw from again; New place in the header starts another.
  return (
    <section className="draft-list form-stack" aria-labelledby="draft-overview">
      <h2 id="draft-overview" className="visually-hidden">Overview</h2>
      {work.brief ? <form className="draft-line" onSubmit={redraw}>
        <label htmlFor="draft-line-again">Drawn from</label>
        <div className="draft-line-row">
          <input autoComplete="off" id="draft-line-again" value={line} maxLength={400} placeholder="e.g. a cold fishing town, 1920s" onChange={(event) => setLine(event.target.value)} />
          <button type="submit" className="button" aria-disabled={busy}><FilePlus2 aria-hidden="true" />Draw it up</button>
        </div>
        <div className="form-actions wrap">
          <button type="button" className="button" disabled={busy} onClick={() => careful(() => void draw(work.line, newSeed(), {}), 'Take another go at this line?', 'Another take')}><Dices aria-hidden="true" />Another take</button>
          <button type="button" className="button" disabled={busy} onClick={() => onRoll('name')}><Dices aria-hidden="true" />Another name</button>
        </div>
      </form> : <p className="subtle">Opened from a file. Roll again needs the line a place was drawn from, so it is off for this one.</p>}
      <TextInput label="Name" value={work.definition.name} maxLength={120} onChange={(name) => change({ name })} hint={work.saved ? 'Saved with your cities, so its id stays as it is.' : undefined} />
      <SummaryField work={work} onChange={(summary) => change({ summary })} onRewrite={rewrite} />
      <div className="draft-pair">
        <TextInput label="Region" value={work.definition.region} maxLength={120} onChange={(region) => change({ region })} />
        <TextInput label={work.definition.enclosed ? 'Kind of ship' : 'Country or realm'} value={work.definition.country} maxLength={120} onChange={(country) => change({ country })} />
      </div>
      {!work.definition.enclosed && <WeatherChoice definition={work.definition} onChange={(climate) => setWork((current) => current && settle(current, withWeather(current.definition, climate)))} />}
      <Neighbours definition={work.definition} cities={cities.data ?? []} onChange={(index, change) => setWork((current) => current && settle(current, changeNeighbour(current.definition, index, change)))} />
      {anchor && <p className="subtle">Money, prices, holidays and names follow {anchor.name}, which ships with Companion, so a day here costs what a day there does.</p>}
    </section>
  )
}

/** The place's weather, from the climates the table draws with; a climate of the file's own stays until changed. */
function WeatherChoice({ definition, onChange }: { definition: Definition; onChange: (climate: Weather['climate']) => void }) {
  const weathers = useWeathers()
  if (!weathers) return null
  const now = weatherOf(weathers, definition)
  const own = definition.climate ? 'Its own weather' : 'None yet'
  const options = { ...(now ? {} : { '': own }), ...Object.fromEntries(weathers.map((item) => [item.id, item.name])) }
  return <Choice label="Weather" value={now?.id ?? ''} options={options} hint={now?.climate.summary}
    onChange={(id) => { const found = weathers.find((item) => item.id === id); if (found) onChange(found.climate) }} />
}

/** The climates a place can have (companion/world/draft/fill.py), which never change while the table is open. */
function useWeathers(): Weather[] | undefined {
  return useQuery({ queryKey: ['draft-weather'], queryFn: () => api<Weather[]>('/world/draft/weather'), staleTime: Infinity }).data
}

/** Other places of the same world, and how long the journey there takes: trips and postcards go between them. Each
 * reads as a row, "Pellmouth · 3 hours by ferry", opening to its fields like every other list. */
function Neighbours({ definition, cities, onChange }: { definition: Definition; cities: CityListing[]; onChange: (index: number, change: Partial<Neighbour> | null) => void }) {
  const [open, setOpen] = useState<number | null>(null)
  const list = definition.neighbours ?? []
  const choices = cities.filter((city) => city.id !== definition.id)
  const name = (id: string) => cities.find((city) => city.id === id)?.name ?? id
  const add = () => { onChange(list.length, { city: choices.find((city) => !list.some((item) => item.city === city.id))?.id ?? '' }); setOpen(list.length) }
  return (
    <section className="draft-neighbours" aria-labelledby="draft-neighbours">
      <h3 id="draft-neighbours">Nearby places</h3>
      <p className="subtle">Other places in the same world that people here travel to, for trips and postcards. It works both ways.</p>
      {list.length > 0 && <ul className="draft-items">
        {list.map((neighbour, index) => (
          <ItemRow key={index} item={{ id: `neighbour-${index}`, name: neighbour.city ? name(neighbour.city) : 'Choose a place', summary: '' }}
            meta={`${journey(neighbour.hours)}${neighbour.by?.trim() ? ` by ${neighbour.by.trim()}` : ''}`} open={open === index}
            onOpen={(id) => setOpen(id === null ? null : index)} onRemove={() => { onChange(index, null); setOpen(null) }}>
            <div className="draft-pair">
              <Field label="Place">{(id) => <select id={id} value={neighbour.city} onChange={(event) => onChange(index, { city: event.target.value })}>
                {!neighbour.city && <option value="">Choose a place</option>}
                {!choices.some((city) => city.id === neighbour.city) && neighbour.city && <option value={neighbour.city}>{name(neighbour.city)}</option>}
                {choices.map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}
              </select>}</Field>
              <Field label="Journey">{(id) => <select id={id} value={neighbour.hours} onChange={(event) => onChange(index, { hours: Number(event.target.value) })}>
                {[...new Set([...JOURNEY_HOURS, neighbour.hours])].sort((a, b) => a - b).map((hours) => <option key={hours} value={hours}>{journey(hours)}</option>)}
              </select>}</Field>
            </div>
            <TextInput label="By" value={neighbour.by ?? ''} maxLength={40} placeholder="e.g. the coast steamer" hint="How people get there. Leave it empty if it doesn't matter." onChange={(by) => onChange(index, { by })} />
          </ItemRow>
        ))}
      </ul>}
      {list.length < 20 && <button type="button" className="text-button draft-add" onClick={add}><Plus aria-hidden="true" />Add a nearby place</button>}
    </section>
  )
}

/** The place's summary: written from the place until the user writes their own, and back again on request. */
function SummaryField({ work, onChange, onRewrite }: { work: Work; onChange: (summary: string) => void; onRewrite: () => void }) {
  const follows = work.brief !== null && !work.summaryEdited
  return (
    <div className="draft-summary">
      <TextArea label="What it is like" value={work.definition.summary} maxLength={400} rows={3} onChange={onChange}
        hint={follows ? 'Follows the name and the parts of town until you write your own.' : undefined} />
      {work.brief && !follows && <button type="button" className="text-button" onClick={onRewrite}>Write it from the place again</button>}
    </div>
  )
}

/** What Companion would make of the place if it were saved now. */
function CheckPanel({ check, opened }: { check: CheckState; opened?: string[] }) {
  if (check.state === 'checking') return <p className="subtle draft-checking"><LoaderCircle aria-hidden="true" className="spin" />Checking…</p>
  if (check.state === 'failed') return <section className="draft-list form-stack" aria-labelledby="draft-check"><h2 id="draft-check">Check</h2><Notice tone="error">Companion would not load this yet. {check.message}</Notice></section>
  const { warnings, notes, summary } = check.checked
  const counts = summary.counts
  return (
    <section className="draft-list form-stack" aria-labelledby="draft-check">
      <h2 id="draft-check">Check</h2>
      {!warnings.length && !notes.length && <Notice tone="success">Ready. Companion loads it as it is, with nothing to fix.</Notice>}
      {warnings.map((warning) => <Notice key={warning} tone="warning">{warning}</Notice>)}
      {opened && opened.length > 0 && <details className="draft-opened">
        <summary>What came over from the world map ({opened.length})</summary>
        <ul className="city-notes">{opened.map((note) => <li key={note}>{note}</li>)}</ul>
      </details>}
      {notes.length > 0 && <div><p>Companion tidies these on the way in:</p><ul className="city-notes">{groupNotes(notes).map((note) => <li key={note}>{note}</li>)}</ul></div>}
      <p className="subtle">{[
        `${counts.neighborhoods} ${plural(counts.neighborhoods, summary.enclosed ? 'deck' : 'neighborhood')}`, `${counts.places} ${plural(counts.places, 'place')}`,
        `${counts.employers} ${plural(counts.employers, 'employer')}`].join(', ')}, {counts.annual_events} {plural(counts.annual_events, 'yearly event')}.</p>
    </section>
  )
}
