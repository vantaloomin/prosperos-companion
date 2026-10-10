import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Home, MapPin, Undo2, X } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { OUTING_STATES, TOGETHER_KEY, outingNote, outingTitle, outingWhen, placeLine, shown, tripDays, tripTitle, undoText, type Outing } from './outingText'
import { useTogether } from './useTogether'

/** Plans with the user. The companion picked the places; the user can call them off (with Undo for the rest of the
 * day), send them somewhere else, or head home early (with Undo for a minute or two). */
export function OutTogether({ name }: { name: string }) {
  const client = useQueryClient()
  const data = useTogether()
  const [error, setError] = useState('')
  const outings = shown(data.data?.outings ?? [])
  if (!outings.length) return null
  const act = async (path: string) => {
    setError('')
    try { await api(path, {}) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
    void client.invalidateQueries({ queryKey: ['today'] })
  }
  return (
    <section className="today-section" aria-labelledby="together-heading">
      <h2 id="together-heading">Out together</h2>
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="event-list together-list">
        {outings.map((outing) => <OutingItem key={outing.id} outing={outing} name={name} act={act} />)}
      </ul>
    </section>
  )
}

function OutingItem({ outing, name, act }: { outing: Outing; name: string; act: (path: string) => Promise<void> }) {
  const changed = undoText(outing)
  if (changed) return (
    <li className="together-item together-undo">
      <p><strong>{outingTitle(outing)}</strong> <span className="subtle">{changed}</span></p>
      <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/undo`)}><Undo2 aria-hidden="true" />Undo</button>
    </li>
  )
  const note = outingNote(outing, name)
  return (
    <li className="together-item">
      <div className="together-head">
        <strong>{outingTitle(outing)}</strong>
        <span className="badge">{OUTING_STATES[outing.state]}</span>
      </div>
      <p className="subtle">{outingWhen(outing, name)} · {placeLine(outing.place)} <a className="text-button show-on-map" href={`#map/${encodeURIComponent(outing.place.id)}`}>Show on map</a></p>
      {note && <p className="subtle">{note}</p>}
      {outing.state === 'planned' && <div className="together-actions">
        <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/elsewhere`)}><MapPin aria-hidden="true" />Somewhere else</button>
        <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/cancel`)}><X aria-hidden="true" />Call it off</button>
      </div>}
      {outing.state === 'now' && <div className="together-actions">
        <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/home`)}><Home aria-hidden="true" />Head home</button>
      </div>}
    </li>
  )
}

/** The companion's own trips: their life, so there is nothing to override. */
export function Trips({ name }: { name: string }) {
  const trips = shown(useTogether().data?.trips ?? [])
  if (!trips.length) return null
  return (
    <section className="today-section" aria-labelledby="trips-heading">
      <h2 id="trips-heading">Trips</h2>
      <ul className="event-list together-list">
        {trips.map((trip) => (
          <li key={trip.id} className="together-item">
            <div className="together-head">
              <strong>{tripTitle(trip)}</strong>
              <span className="badge">{trip.state === 'now' ? 'Away now' : OUTING_STATES[trip.state]}</span>
            </div>
            <p className="subtle">{tripDays(trip)}{trip.cost_text ? ` · about ${trip.cost_text}` : ''}</p>
            {trip.postcard_message_id && <p className="subtle">{name} sent you a postcard{trip.landmark ? ` of ${trip.landmark.name}` : ''}.</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}
