import { useState, type FormEvent, type MouseEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion } from '../../types'
import { DRAFT_KEY, newDraft, readDraft, writeDraft } from '../conversation/draft'
import { historyLine, isHome, spotList, suggestion, type MapHood, type MapPlace } from './mapText'

interface Props { inline?: boolean; place: MapPlace; city: string; hoods: MapHood[]; enclosed: boolean; story: boolean; companion: Companion; onClose: () => void; go: (view: View) => void }

const storage = () => { try { return window.localStorage } catch { return undefined } }

/** A tapped place: what it is, what happened there with them, who is usually there, and where to go next. A home says
 * whose it is; theirs and the places in town can be edited here, and the user's own home is changed where they live. */
export function PlaceCard({ inline, place, city, hoods, enclosed, story, companion, onClose, go }: Props) {
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
  const someone = isHome(place)
  return (
    <aside className={inline ? 'map-card inline' : 'map-card'} aria-label={place.name}>
      <header>
        <div><h2>{place.name}</h2><p className="subtle">{[someone ? place.relation : place.kind, place.hood].filter(Boolean).join(' · ')}</p></div>
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
      </header>
      {editing ? <EditPlace place={place} hoods={hoods} enclosed={enclosed} name={name} onDone={() => setEditing(false)} />
        : <PlaceFacts place={place} name={name} editable={place.id === '~home' || !someone} onEdit={() => setEditing(true)} />}
      {!editing && <PlaceDetails place={place} name={name} timezone={companion.version.definition.timezone} story={story} goThere={() => void goThere()} suggest={suggest} go={go} />}
      {error && <p className="field-error" role="alert">{error}</p>}
    </aside>
  )
}

interface DetailsProps { place: MapPlace; name: string; timezone?: string; story: boolean; goThere: () => void; suggest: () => void; go: (view: View) => void }

/** What happened there with them, who is usually there, and what to do next: nothing for someone else's home. */
function PlaceDetails({ place, name, timezone, story, goThere, suggest, go }: DetailsProps) {
  const home = place.id === '~home'
  return <>
    {place.history.length > 0 && <section>
      <h3>With {name}</h3>
      <ul className="map-history">{place.history.map((item) => <li key={item.id}>
        <button type="button" className="text-button" onClick={() => go('today')}>{historyLine(item, timezone)}</button>
      </li>)}</ul>
    </section>}
    {place.regulars.length > 0 && <p className="subtle">Regulars: {place.regulars.join(', ')}</p>}
    {place.id === '~you' ? <YourHome /> : (home || !isHome(place)) && <PlaceAction story={story} home={home ? name : null} here={place.pins.includes('scene')} goThere={goThere} suggest={suggest} />}
  </>
}

/** What the card says about a place or a home: where it is approximate, its description and what is inside. */
function PlaceFacts({ place, name, editable, onEdit }: { place: MapPlace; name: string; editable: boolean; onEdit: () => void }) {
  const home = place.id === '~home'
  return <>
    {!isHome(place) && <p className="subtle map-approx">Location approximate</p>}
    {place.about && <p>{place.about.charAt(0).toUpperCase() + place.about.slice(1).replace(/[.\s]*$/, '.')}</p>}
    {place.spots.length > 0 && <p className="subtle">Inside: {place.spots.join(', ')}</p>}
    {home && <p className="subtle">The same home as on {name}'s Character page; changes here show there too.</p>}
    {editable && <button type="button" className="button map-edit" onClick={onEdit}>{home ? 'Edit home' : 'Edit inside'}</button>}
  </>
}

/** Their home's neighborhood and rooms, or what is inside a place, in the user's words. Saved for the whole app:
 * their Home section, chat, pictures and Story mode use the same. */
function EditPlace({ place, hoods, enclosed, name, onDone }: { place: MapPlace; hoods: MapHood[]; enclosed: boolean; name: string; onDone: () => void }) {
  const client = useQueryClient()
  const home = place.id === '~home'
  const [about, setAbout] = useState(place.about ?? '')
  const [hood, setHood] = useState(place.hood_id)
  const [inside, setInside] = useState(place.spots.join(', '))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    try {
      await saveEdits(place, about.trim(), hood, spotList(inside))
      await Promise.all([client.invalidateQueries({ queryKey: ['city-map'] }), client.invalidateQueries({ queryKey: ['home'] })])
      onDone()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That could not be saved.')
    } finally { setSaving(false) }
  }
  const usual = (event: MouseEvent) => { event.preventDefault(); setInside('') }
  const words = home ? { label: 'Rooms', example: 'Such as the kitchen, the bedroom', used: `${name}'s days, pictures and Story mode use these rooms.`, set: place.rooms_set }
    : { label: 'Inside', example: 'Such as the bar, the back room', used: "Everyone's days and Story mode use these.", set: place.spots_set }
  return (
    <form className="map-edit-form" onSubmit={(event) => void save(event)}>
      {home && <HomeFields about={about} setAbout={setAbout} was={place.about ?? ''} hood={hood} setHood={setHood} hoods={hoods} part={enclosed ? 'Deck' : 'Neighborhood'} name={name} />}
      <label htmlFor="map-inside">{words.label}</label>
      <textarea id="map-inside" className="grow-box" rows={2} value={inside} maxLength={480} aria-describedby="map-inside-hint" placeholder={words.example} onChange={(event) => { setInside(event.target.value); grow(event.target) }} />
      <small id="map-inside-hint" className="subtle">
        Separate with commas. {words.used}
        {words.set && <> <button type="button" className="text-button inline" onClick={usual}>Use the usual ones</button></>}
      </small>
      {error && <p className="field-error" role="alert">{error}</p>}
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={saving}>Save</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
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

/** With Story mode on, moving the scene there (not offered where the scene already is); else an invitation draft: for
 * their own home (`home` is their name), dinner at their place (they cook). */
function PlaceAction({ story, home, here, goThere, suggest }: { story: boolean; home: string | null; here: boolean; goThere: () => void; suggest: () => void }) {
  if (home !== null) return story ? null : <button type="button" className="button primary" onClick={suggest}>Suggest dinner at {home}'s place</button>
  if (!story) return <button type="button" className="button primary" onClick={suggest}>Suggest going together</button>
  return here ? null : <button type="button" className="button primary" onClick={goThere}>Go there</button>
}

