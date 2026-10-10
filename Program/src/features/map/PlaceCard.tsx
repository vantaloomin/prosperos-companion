import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion } from '../../types'
import { DRAFT_KEY, newDraft, readDraft, writeDraft } from '../conversation/draft'
import { historyLine, suggestion, type MapPlace } from './mapText'

interface Props { place: MapPlace; city: string; story: boolean; companion: Companion; onClose: () => void; go: (view: View) => void }

const storage = () => { try { return window.localStorage } catch { return undefined } }

/** A tapped place: what it is, what happened there with them, who is usually there, and where to go next. */
export function PlaceCard({ place, city, story, companion, onClose, go }: Props) {
  const client = useQueryClient()
  const [error, setError] = useState('')
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
  }
  const home = place.id === '~home'
  return (
    <aside className="map-card" aria-label={place.name}>
      <header>
        <div><h2>{place.name}</h2><p className="subtle">{[home ? '' : place.kind, place.hood].filter(Boolean).join(' · ')}</p></div>
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
      </header>
      {!home && <p className="subtle map-approx">Location approximate</p>}
      {place.spots.length > 0 && <p className="subtle">Inside: {place.spots.join(', ')}</p>}
      {place.history.length > 0 && <section>
        <h3>With {name}</h3>
        <ul className="map-history">{place.history.map((item) => <li key={item.id}>
          <button type="button" className="text-button" onClick={() => go('today')}>{historyLine(item, companion.version.definition.timezone)}</button>
        </li>)}</ul>
      </section>}
      {place.regulars.length > 0 && <p className="subtle">Regulars: {place.regulars.join(', ')}</p>}
      {!home && (story
        ? <button type="button" className="button primary" onClick={() => void goThere()}>Go there</button>
        : <button type="button" className="button primary" onClick={suggest}>Suggest going together</button>)}
      {error && <p className="field-error" role="alert">{error}</p>}
    </aside>
  )
}
