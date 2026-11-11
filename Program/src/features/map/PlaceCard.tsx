import { useState, type FormEvent, type MouseEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Pencil, X } from 'lucide-react'
import { InfoTip } from '../../components/InfoTip'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion } from '../../types'
import { HISTORY_KEY } from '../../companion'
import { DRAFT_KEY, newDraft, readDraft, writeDraft } from '../conversation/draft'
import { WHERE_KEY } from '../conversation/whereText'
import { TOGETHER_KEY } from '../today/outingText'
import { ADDED_KINDS, dropByFound, dropByHint, dropByLabel, dropByLines, historyLine, isHome, spotList, suggestHint, suggestion, type DropByResult, type MapHood, type MapPlace } from './mapText'

interface Props { inline?: boolean; place: MapPlace; city: string; hoods: MapHood[]; enclosed: boolean; story: boolean; companion: Companion; onClose: () => void; go: (view: View) => void
  /** A place added when the user named it was taken off the map: the map closes the card and offers Undo. */
  onRemoved?: (place: MapPlace) => void }

const storage = () => { try { return window.localStorage } catch { return undefined } }

/** A tapped place: what it is, what happened there with them, who is usually there, and where to go next. A home says
 * whose it is; theirs and the places in town can be edited here, and the user's own home is changed where they live. */
export function PlaceCard({ inline, place, city, hoods, enclosed, story, companion, onClose, go, onRemoved }: Props) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const name = companion.version.name
  const goThere = async () => {
    try {
      await api('/story/scene', { city_id: city, place_id: place.id }, 'PUT')
      void client.invalidateQueries({ queryKey: ['story'] })
      go('story')
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'The story could not move there.') }
  }
  // Puts a draft in their composer and opens the chat; it never sends anything on its own.
  const suggest = () => {
    const draft = readDraft(storage(), DRAFT_KEY)
    const line = suggestion(place)
    writeDraft(storage(), draft.text.trim() ? { ...draft, text: `${draft.text.trimEnd()} ${line}` } : newDraft(line, undefined, draft.pictures), DRAFT_KEY)
    go('conversation')
    window.setTimeout(() => document.getElementById('composer-text')?.focus(), 0)  // once the chat has drawn
  }
  // Surprise visits (companion/life/drop_by.py): in, the chat opens on their first words; else the card says why not.
  const [found, setFound] = useState('')
  const [going, setGoing] = useState(false)
  const dropBy = async () => {
    setGoing(true); setFound(''); setError('')
    try {
      const result = await api<DropByResult>('/life/drop-by', { place: place.id === '~home' ? 'home' : 'work' })
      for (const key of [WHERE_KEY, HISTORY_KEY, TOGETHER_KEY, ['city-map'], ['chats']]) void client.invalidateQueries({ queryKey: key })
      if (result.result === 'in' || result.result === 'work') go('conversation')
      else setFound(dropByFound(result, name))
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'You could not get there.') }
    finally { setGoing(false) }
  }
  const visit = { found, going, dropBy: () => void dropBy() }
  return (
    <aside className={inline ? 'map-card inline' : 'map-card'} aria-label={place.name}>
      <CardHeader place={place} name={name} editable={!editing && (place.id === '~home' || !isHome(place))} onEdit={() => setEditing(true)} onClose={onClose} />
      {editing ? <EditPlace place={place} hoods={hoods} enclosed={enclosed} name={name} onDone={() => setEditing(false)} onRemoved={onRemoved} />
        : <PlaceFacts place={place} />}
      {!editing && <PlaceDetails place={place} name={name} timezone={companion.version.definition.timezone} story={story} goThere={() => void goThere()} suggest={suggest} go={go} visit={visit} />}
      {error && <p className="field-error" role="alert">{error}</p>}
    </aside>
  )
}

/** The place's name and kind, with Edit as a quiet pen beside ×, so the card's actions read Drop by, then the
 * invitation (Iris, 2026-11-03). */
function CardHeader({ place, name, editable, onEdit, onClose }: { place: MapPlace; name: string; editable: boolean; onEdit: () => void; onClose: () => void }) {
  const home = place.id === '~home'
  const label = home ? 'Edit home' : place.added ? 'Edit place' : 'Edit inside'
  return (
    <header>
      <div><h2>{place.name}</h2><p className="subtle">{[isHome(place) ? place.relation : place.kind, place.hood].filter(Boolean).join(' · ')}</p></div>
      <div className="map-card-tools">
        {editable && <button type="button" className="icon-button" aria-label={label}
          title={home ? `Edit home. Changes here show on ${name}'s Character page too.` : label} onClick={onEdit}><Pencil aria-hidden="true" /></button>}
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
    </header>
  )
}

interface Visit { found: string; going: boolean; dropBy: () => void }
interface DetailsProps { place: MapPlace; name: string; timezone?: string; story: boolean; goThere: () => void; suggest: () => void; go: (view: View) => void; visit: Visit }

/** What happened there with them, who is usually there, and what to do next: nothing for someone else's home. */
function PlaceDetails({ place, name, timezone, story, goThere, suggest, go, visit }: DetailsProps) {
  return <>
    {place.history.length > 0 && <section>
      <h3>With {name}</h3>
      <ul className="map-history">{place.history.map((item) => <li key={item.id}>
        <button type="button" className="text-button" onClick={() => go('today')}>{historyLine(item, timezone)}</button>
      </li>)}</ul>
    </section>}
    {place.regulars.length > 0 && <p className="subtle">Regulars: {place.regulars.join(', ')}</p>}
    <NextSteps place={place} name={name} story={story} goThere={goThere} suggest={suggest} visit={visit} />
  </>
}

/** What to do next: drop by (theirs or their work), then an invitation or Story mode's Go there; for the user's own
 * home, where to change it; nothing for someone else's home. */
function NextSteps({ place, name, story, goThere, suggest, visit }: Omit<DetailsProps, 'timezone' | 'go'>) {
  const home = place.id === '~home'
  if (place.id === '~you') return <YourHome />
  if (!home && isHome(place)) return null
  return <>
    {!story && place.drop_by && <DropBy place={place} name={name} visit={visit} />}
    <PlaceAction story={story} name={name} home={home ? name : null} here={place.pins.includes('scene')} goThere={goThere} suggest={suggest} quiet={!story && Boolean(place.drop_by)} />
  </>
}

/** What the card says about a place or a home: where it is approximate, its description and what is inside. */
function PlaceFacts({ place }: { place: MapPlace }) {
  return <>
    {!isHome(place) && <p className="subtle map-approx">{place.added ? 'Added when you named it · Location approximate' : 'Location approximate'}</p>}
    {place.about && <p>{place.about.charAt(0).toUpperCase() + place.about.slice(1).replace(/[.\s]*$/, '.')}</p>}
    {place.spots.length > 0 && <p className="subtle">Inside: {place.spots.join(', ')}</p>}
  </>
}

/** Their home's neighborhood and rooms, or what is inside a place, in the user's words. Saved for the whole app:
 * their Home section, chat, pictures and Story mode use the same. */
function EditPlace({ place, hoods, enclosed, name, onDone, onRemoved }: { place: MapPlace; hoods: MapHood[]; enclosed: boolean; name: string; onDone: () => void; onRemoved?: (place: MapPlace) => void }) {
  const client = useQueryClient()
  const home = place.id === '~home'
  const [about, setAbout] = useState(place.about ?? '')
  const [hood, setHood] = useState(place.hood_id)
  const [inside, setInside] = useState(place.spots.join(', '))
  const [title, setTitle] = useState(place.name)
  const [kind, setKind] = useState(place.kind)
  const { error, saving, run } = useRun(onDone)
  const save = (event: FormEvent) => {
    event.preventDefault()
    void run(async () => {
      if (place.added) await saveAdded(place, { name: title.trim(), kind, neighborhood: hood, about: about.trim() })
      await saveEdits(place, about.trim(), hood, spotList(inside))
      await Promise.all([client.invalidateQueries({ queryKey: ['city-map'] }), client.invalidateQueries({ queryKey: ['home'] })])
    }, 'That could not be saved.')
  }
  const usual = (event: MouseEvent) => { event.preventDefault(); setInside('') }
  const remove = () => void run(async () => {
    await api(`/life/map/places/${encodeURIComponent(place.id)}`, undefined, 'DELETE')
    onRemoved?.(place)
    await client.invalidateQueries({ queryKey: ['city-map'] })
  }, 'That could not be removed.')
  const words = insideWords(place, name)
  const part = enclosed ? 'Deck' : 'Neighborhood'
  const shared = { about, setAbout, hood, setHood, hoods, part }
  return (
    <form className="map-edit-form" onSubmit={save}>
      {home && <HomeFields {...shared} was={place.about ?? ''} name={name} />}
      {place.added && <AddedFields {...shared} title={title} setTitle={setTitle} kind={kind} setKind={setKind} />}
      <label htmlFor="map-inside">{words.label}</label>
      <textarea id="map-inside" className="grow-box" rows={2} value={inside} maxLength={480} aria-describedby="map-inside-hint" placeholder={words.example} onChange={(event) => { setInside(event.target.value); grow(event.target) }} />
      <small id="map-inside-hint" className="subtle">
        Separate with commas. {words.used}
        {words.set && <> <button type="button" className="text-button inline" onClick={usual}>Use the usual ones</button></>}
      </small>
      {error && <p className="field-error" role="alert">{error}</p>}
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={saving || !title.trim()}>Save</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
      {place.added && <button type="button" className="text-button danger map-remove" disabled={saving} onClick={remove}>Remove from the map</button>}
    </form>
  )
}

/** What the list under the fields is: their home's rooms, or what is inside a place. */
function insideWords(place: MapPlace, name: string) {
  return place.id === '~home'
    ? { label: 'Rooms', example: 'Such as the kitchen, the bedroom', used: `${name}'s days, pictures and Story mode use these rooms.`, set: place.rooms_set }
    : { label: 'Inside', example: 'Such as the bar, the back room', used: "Everyone's days and Story mode use these.", set: place.spots_set }
}

/** Runs a save or a removal, keeping its error and whether it is under way; done once it worked. */
function useRun(onDone: () => void) {
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const run = async (work: () => Promise<void>, failed: string) => {
    setSaving(true)
    try {
      await work()
      onDone()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : failed)
    } finally { setSaving(false) }
  }
  return { error, saving, run }
}

interface AddedFieldsProps { title: string; setTitle: (text: string) => void; kind: string; setKind: (kind: string) => void; about: string; setAbout: (text: string) => void; hood: string; setHood: (id: string) => void; hoods: MapHood[]; part: string }

/** A place added when the user named it: the app filled it in, and every detail is theirs to change. */
function AddedFields({ title, setTitle, kind, setKind, about, setAbout, hood, setHood, hoods, part }: AddedFieldsProps) {
  const kinds = ADDED_KINDS.some(([id]) => id === kind) ? ADDED_KINDS : [[kind, kind.charAt(0).toUpperCase() + kind.slice(1)], ...ADDED_KINDS]
  return <>
    <label htmlFor="map-place-name">Name</label>
    <input id="map-place-name" autoComplete="off" value={title} maxLength={80} onChange={(event) => setTitle(event.target.value)} />
    <label htmlFor="map-place-kind">Kind of place</label>
    <select id="map-place-kind" value={kind} onChange={(event) => setKind(event.target.value)}>
      {kinds.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </select>
    <label htmlFor="map-place-hood">{part}</label>
    <select id="map-place-hood" value={hood} onChange={(event) => setHood(event.target.value)}>
      {[...hoods].sort((a, b) => a.name.localeCompare(b.name)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
    </select>
    <label htmlFor="map-place-about">Description</label>
    <textarea id="map-place-about" className="grow-box" rows={2} value={about} maxLength={300} placeholder="What's it like?" onChange={(event) => { setAbout(event.target.value); grow(event.target) }} ref={(box) => { if (box) grow(box) }} />
  </>
}

/** A place added when the user named it: only what changed is sent. */
async function saveAdded(place: MapPlace, next: { name: string; kind: string; neighborhood: string; about: string }) {
  const change = Object.fromEntries(Object.entries(next).filter(([key, value]) =>
    value !== { name: place.name, kind: place.kind, neighborhood: place.hood_id, about: place.about ?? '' }[key]))
  if (Object.keys(change).length) await api(`/life/map/places/${encodeURIComponent(place.id)}`, change, 'PATCH')
}

interface HomeFieldsProps { about: string; setAbout: (text: string) => void; was: string; hood: string; setHood: (id: string) => void; hoods: MapHood[]; part: string; name: string }

/** Their home's description and neighborhood (deck aboard), the same ones as on their Character page. */
function HomeFields({ about, setAbout, was, hood, setHood, hoods, part, name }: HomeFieldsProps) {
  return <>
    <label htmlFor="map-home-about">Description</label>
    <textarea id="map-home-about" className="grow-box" rows={2} value={about} maxLength={300} placeholder="Such as an apartment above the fighting pits" onChange={(event) => { setAbout(event.target.value); grow(event.target) }} ref={(box) => { if (box) grow(box) }} />
    {about.trim() !== was && <small className="subtle" aria-live="polite">A new description clears the quirks picked for the old one; add your own on {name}'s Character page.</small>}
    <label htmlFor="map-home-hood">{part}</label>
    <select id="map-home-hood" value={hood} onChange={(event) => setHood(event.target.value)}>
      {[...hoods].sort((a, b) => a.name.localeCompare(b.name)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
    </select>
  </>
}

/** Saves what changed: their home's description, rooms and neighborhood (the description first, since a new one that
 * names a neighborhood moves the home there, and a pick made here wins after it), or what is inside a place. */
async function saveEdits(place: MapPlace, about: string, hood: string, spots: string[]) {
  const same = spots.join('|') === place.spots.join('|')
  if (place.id !== '~home') {
    if (!same) await api(`/life/map/places/${encodeURIComponent(place.id)}/inside`, { spots }, 'PUT')
    return
  }
  const described = about && about !== (place.about ?? '')
  const change = { ...(described ? { description: about } : {}), ...(same ? {} : { rooms: spots }) }
  if (place.item_id && Object.keys(change).length) await api(`/life/home/items/${place.item_id}`, change, 'PATCH')
  if (hood !== place.hood_id) await api('/life/map/home', { neighborhood: hood }, 'PUT')
}

/** A text box grows with its text where the browser cannot do it with CSS alone (field-sizing). */
function grow(box: HTMLTextAreaElement) {
  if (typeof CSS !== 'undefined' && CSS.supports('field-sizing', 'content')) return
  box.style.height = 'auto'
  box.style.height = `${box.scrollHeight + 2}px`
}

/** The user's own home: the app picked it, and it is changed with the rest of where they live in this world. */
function YourHome() {
  const change = (event: MouseEvent) => {
    event.preventDefault()
    window.history.pushState({ focus: 'persona-home' }, '', '#worlds')
    window.dispatchEvent(new PopStateEvent('popstate', { state: { focus: 'persona-home' } }))
  }
  return <>
    <p className="subtle">Where you live in this world. The app picked it; you can change it.</p>
    <a className="button" href="#worlds" onClick={change}>Change where you live</a>
  </>
}

/** Surprise visits (companion/life/drop_by.py): going over now, unannounced, to their home or to their work while they
 * are on shift. The state line (on shift until when) sits above; under the button, what it found once tried, else why
 * it is off right now (shown disabled), else at work that it is a short visit. The rest is in its tip (Iris, 2026-11-03). */
function DropBy({ place, name, visit }: { place: MapPlace; name: string; visit: Visit }) {
  const offer = place.drop_by
  if (!offer) return null
  const work = place.id !== '~home'
  const { state, under } = dropByLines(offer, name, work, visit.found)
  return <>
    {state && <p className="subtle">{state}</p>}
    <div className="map-action">
      <button type="button" className="button primary" disabled={!offer.ok || visit.going} onClick={visit.dropBy} aria-describedby={under ? 'map-drop-under' : undefined}>
        {dropByLabel(work, visit.going)}
      </button>
      <InfoTip id="map-drop-tip" label="Drop by" text={work ? `You go over without asking and see ${name} at work.` : dropByHint(name, false)} />
    </div>
    {under && <p id="map-drop-under" className={visit.found ? 'map-drop-found' : 'map-drop-under'} role={visit.found ? 'status' : undefined}>{under}</p>}
  </>
}

/** With Story mode on, moving the scene there (not offered where the scene already is); else an invitation draft: for
 * their own home (`home` is their name), dinner at their place (they cook). Beside Drop by
 * (`quiet`), the invitation is the second button. */
function PlaceAction({ story, name, home, here, goThere, suggest, quiet }: { story: boolean; name: string; home: string | null; here: boolean; goThere: () => void; suggest: () => void; quiet: boolean }) {
  const kind = quiet ? 'button' : 'button primary'
  if (!story) return <div className="map-action">
    <button type="button" className={kind} onClick={suggest}>{home !== null ? `Suggest dinner at ${home}'s place` : 'Suggest going together'}</button>
    <InfoTip id="map-suggest-tip" label="the invitation" text={suggestHint(name)} />
  </div>
  if (home !== null) return null
  return here ? null : <button type="button" className="button primary" onClick={goThere}>Go there</button>
}

