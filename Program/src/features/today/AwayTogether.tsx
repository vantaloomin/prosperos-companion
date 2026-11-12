import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, Home, Undo2, X } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { WHERE_KEY } from '../conversation/whereText'
import { firstName } from '../character/panelText'
import { TOGETHER_KEY, tripDays, tripTitle, tripTravel, type Trip } from './outingText'

/** Trips away together on the 1.3 Today (Iris 2026-11-03): one under way sits in the Now card with Head home as a quiet
 * action; those still to come are rows in Coming up, with errand-style row actions (icon and tooltip on desktop, words
 * on a phone). */
function useAct() {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const act = async (path: string, body: object = {}) => {
    setError('')
    try { await api(path, body) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
    void client.invalidateQueries({ queryKey: ['today'] })
    void client.invalidateQueries({ queryKey: ['routine'] })
    void client.invalidateQueries({ queryKey: WHERE_KEY })
  }
  return { act, error }
}

/** In the Now card while away: Head home, then "Heading home early." with Undo for a minute or two. */
export function AwayNowAction({ trip }: { trip: Trip | null }) {
  const { act, error } = useAct()
  if (!trip) return null
  if (trip.home_undo) return (
    <p className="row-sub away-now-action">Heading home early. <button type="button" className="text-button inline" onClick={() => void act(`/life/trips/${trip.id}/stay`)}><Undo2 aria-hidden="true" />Undo</button></p>
  )
  if (trip.start_date === trip.end_date) return null
  return <>
    {error && <Notice tone="error">{error}</Notice>}
    <p className="away-now-action"><button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/home`)}><Home aria-hidden="true" />Head home</button></p>
  </>
}

type Place = { key: string; name: string; summary: string; by: string; first: boolean }

/** Change place: the places those days reach that they can pay for, the one first planned first; picking one moves
 * the trip there, the same days (tester 2026-11-12: the old map pin cycled places and read as a map link). */
function PlacePicker({ trip, onPick, onClose }: { trip: Trip; onPick: (key: string) => void; onClose: () => void }) {
  const [places, setPlaces] = useState<Place[] | null>(null)
  const [failed, setFailed] = useState('')
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onClose])
  useEffect(() => {
    let live = true
    api<Place[]>(`/life/trips/${trip.id}/places`)
      .then((found) => { if (live) setPlaces(found) })
      .catch((failure: unknown) => { if (live) setFailed(failure instanceof Error ? failure.message : 'That did not work.') })
    return () => { live = false }
  }, [trip.id])
  if (failed) return <Notice tone="error">{failed}</Notice>
  if (!places) return <p className="subtle away-places-wait">Looking…</p>
  if (!places.length) return <p className="subtle away-places-wait">Nowhere else fits those days. <button type="button" className="text-button inline" onClick={onClose}>Close</button></p>
  return (
    <ul className="away-places" aria-label={`Places for ${tripTitle(trip, '')}`}>
      {places.map((place) => (
        <li key={place.key}>
          <button type="button" className="away-place" onClick={() => onPick(place.key)}>
            <span className="away-place-name">{place.name.charAt(0).toUpperCase() + place.name.slice(1)}</span>
            <span className="subtle">{[place.first && 'First plan', place.by && `by ${place.by}`].filter(Boolean).join(' · ')}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}

/** Coming up: "Away in Asheville with Mira", its days, how they get there and their share, with Change place and
 * Call it off (Undo once called off). */
export function AwayRows({ trips, name }: { trips: Trip[]; name: string }) {
  const { act, error } = useAct()
  const [picking, setPicking] = useState('')
  const first = firstName(name)
  return <>
    {error && <Notice tone="error">{error}</Notice>}
    <ul className="admin-list">
      {trips.map((trip) => {
        const title = tripTitle(trip, first)
        const travel = tripTravel(trip)
        const when = [tripDays(trip), travel, trip.cost_text && `${first}'s share about ${trip.cost_text}`].filter(Boolean).join(' · ')
        const open = picking === trip.id
        return (
          <li key={trip.id} className={trip.state === 'cancelled' ? 'admin-item admin-skipped' : 'admin-item'}>
            <div className="admin-head"><strong>{title}</strong></div>
            <div className="admin-when">
              <p className="subtle">{trip.state === 'cancelled' ? 'Called off.' : when}</p>
              {trip.state === 'cancelled'
                ? <button type="button" className="text-button" aria-label={`Undo calling off ${title}`} onClick={() => void act(`/life/trips/${trip.id}/undo`)}><Undo2 aria-hidden="true" />Undo</button>
                : <span className="admin-actions">
                    <button type="button" className="text-button admin-move" aria-label={`Change place for ${title}`} aria-expanded={open} title="Change place" onClick={() => setPicking(open ? '' : trip.id)}><ArrowLeftRight aria-hidden="true" /><span className="admin-move-words">Change place</span></button>
                    <button type="button" className="text-button admin-move" aria-label={`Call off ${title}`} title="Call it off" onClick={() => void act(`/life/trips/${trip.id}/cancel`)}><X aria-hidden="true" /><span className="admin-move-words">Call it off</span></button>
                  </span>}
            </div>
            {open && trip.state !== 'cancelled' && <PlacePicker trip={trip} onClose={() => setPicking('')}
              onPick={(key) => { setPicking(''); void act(`/life/trips/${trip.id}/elsewhere`, { key }) }} />}
          </li>
        )
      })}
    </ul>
  </>
}
