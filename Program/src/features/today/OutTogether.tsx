import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Footprints, Home, Hourglass, MapPin, Moon, Undo2, X } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { WHERE_KEY } from '../conversation/whereText'
import { firstName } from '../character/panelText'
import { openWedding } from '../character/weddingText'
import { OUTING_STATES, TOGETHER_KEY, bigDayLine, meetLine, outingNote, outingPlace, outingTitle, outingWhen, peopleLine, shown, tripDays, tripTitle, tripTravel, undoText, type Outing, type Trip } from './outingText'
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
    void client.invalidateQueries({ queryKey: WHERE_KEY })  // The chat strip: under way, or on longer.
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
      <p className="subtle">{outingWhen(outing, name)} · {outingPlace(outing)}{outing.place.kind !== 'family-home' && !outing.place.id.startsWith('~') && <> <a className="text-button show-on-map" href={`#map/${encodeURIComponent(outing.place.id)}`}>Show on map</a></>}</p>
      {peopleLine(outing.place, outing.state) && <p className="subtle">{peopleLine(outing.place, outing.state)}</p>}
      {bigDayLine(outing, firstName(name)) && <p className="subtle">{bigDayLine(outing, firstName(name))}</p>}
      {note && <p className="subtle">{note}</p>}
      <MeetLine outing={outing} />
      <SitterLine outing={outing} />
      {outing.state === 'planned' && <Planned outing={outing} name={name} act={act} />}
      {outing.state === 'now' && <Now outing={outing} act={act} />}
    </li>
  )
}

/** How it plays out: no "Go there" step, they are simply there together when it starts, and the chat is the meeting. */
function MeetLine({ outing }: { outing: Outing }) {
  const line = meetLine(outing)
  if (!line) return null
  return <p className="subtle together-how">{line}{outing.state === 'now' && <> <a className="text-button inline" href="#conversation">Talk face to face</a></>}</p>
}

/** An evening out with a child of yours at home: who is watching them that night (words only). */
function SitterLine({ outing }: { outing: Outing }) {
  if (!outing.sitter || outing.state === 'cancelled') return null
  return <p className="subtle">{outing.sitter.text}</p>
}

/** Stay longer when their next hour is free; Head home, or Call it a night after a long day: your wedding, or a big day in their circle (not a funeral). */
function Now({ outing, act }: { outing: Outing; act: (path: string) => Promise<void> }) {
  const long = outing.activity === 'wedding' || (outing.activity === 'big-day' && !outing.place.quiet)
  return (
    <div className="together-actions">
      {outing.longer_ok && <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/longer`)}><Hourglass aria-hidden="true" />Stay longer</button>}
      <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/home`)}>{long ? <><Moon aria-hidden="true" />Call it a night</> : <><Home aria-hidden="true" />Head home</>}</button>
    </div>
  )
}

/** Go now when they are free before the time, call it off or somewhere else; the wedding is changed on its card on the Character page (companion/life/wedding.py),
 * and a big day is theirs, so the user can only say they can't make it (companion/life/big_days.py). */
function Planned({ outing, name, act }: { outing: Outing; name: string; act: (path: string) => Promise<void> }) {
  if (outing.activity === 'wedding') return (
    <p className="subtle">Planned with {firstName(name)}. <a className="text-button inline" href="#character" onClick={openWedding}>Change the plan</a></p>
  )
  if (outing.activity === 'big-day') return (
    <div className="together-actions">
      <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/cancel`)}><X aria-hidden="true" />Can't make it</button>
    </div>
  )
  return (
    <div className="together-actions">
      {outing.early && <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/now`)}><Footprints aria-hidden="true" />Go now</button>}
      {outing.activity !== 'dinner-in' && outing.activity !== 'meet-family' && <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/elsewhere`)}><MapPin aria-hidden="true" />Somewhere else</button>}
      <button type="button" className="text-button" onClick={() => void act(`/life/outings/${outing.id}/cancel`)}><X aria-hidden="true" />Call it off</button>
    </div>
  )
}

/** The companion's own trips: their life, so there is nothing to override. Weekend visits with the user across the
 * distance (companion/life/long_distance.py) sit among them, and those the user can call off before they start (with
 * Undo for a while after). */
export function Trips({ name }: { name: string }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const trips = shown(useTogether().data?.trips ?? [])
  if (!trips.length) return null
  const act = async (path: string) => {
    setError('')
    try { await api(path, {}) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
    void client.invalidateQueries({ queryKey: ['today'] })
    void client.invalidateQueries({ queryKey: WHERE_KEY })
  }
  return (
    <section className="today-section" aria-labelledby="trips-heading">
      <h2 id="trips-heading">Trips</h2>
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="event-list together-list">
        {trips.map((trip) => <TripItem key={trip.id} trip={trip} name={name} act={act} />)}
      </ul>
    </section>
  )
}

function TripItem({ trip, name, act }: { trip: Trip; name: string; act: (path: string) => Promise<void> }) {
  if (trip.state === 'cancelled') return (
    <li className="together-item together-undo">
      <p><strong>{tripTitle(trip, name)}</strong> <span className="subtle">Called off.</span></p>
      <button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/undo`)}><Undo2 aria-hidden="true" />Undo</button>
    </li>
  )
  if (trip.home_undo) return (
    <li className="together-item together-undo">
      <p><strong>{tripTitle(trip, name)}</strong> <span className="subtle">Heading home early.</span></p>
      <button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/stay`)}><Undo2 aria-hidden="true" />Undo</button>
    </li>
  )
  return (
    <li className="together-item">
      <div className="together-head">
        <strong>{tripTitle(trip, name)}</strong>
        <span className="badge">{trip.state === 'now' ? (trip.visit ? 'Together now' : 'Away now') : OUTING_STATES[trip.state]}</span>
      </div>
      <p className="subtle">{tripMeta(trip, name)}</p>
      {trip.postcard_message_id && <p className="subtle">{name} sent you a postcard{trip.landmark ? ` of ${trip.landmark.name}` : ''}.</p>}
      <TripActions trip={trip} act={act} />
    </li>
  )
}

/** "Fri, Oct 16 – Sun, Oct 18 · By plane · Mira spends about $900". */
function tripMeta(trip: Trip, name: string): string {
  const travel = tripTravel(trip)
  const cost = trip.cost_text ? ` · ${trip.visit ? `${name} spends about` : 'about'} ${trip.cost_text}` : ''
  return `${tripDays(trip)}${travel ? ` · ${travel}` : ''}${cost}`
}

/** A visit or trip together still to come: Somewhere else (a trip together) and Call it off; under way, a trip
 * together can end early with Head home early. */
function TripActions({ trip, act }: { trip: Trip; act: (path: string) => Promise<void> }) {
  const together = trip.visit === 'together'
  if (trip.visit && trip.state === 'planned') return (
    <div className="together-actions">
      {together && <button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/elsewhere`)}><MapPin aria-hidden="true" />Somewhere else</button>}
      <button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/cancel`)}><X aria-hidden="true" />Call it off</button>
    </div>
  )
  if (!together || trip.state !== 'now' || trip.start_date === trip.end_date) return null
  return (
    <div className="together-actions">
      <button type="button" className="text-button" onClick={() => void act(`/life/trips/${trip.id}/home`)}><Home aria-hidden="true" />Head home early</button>
    </div>
  )
}
