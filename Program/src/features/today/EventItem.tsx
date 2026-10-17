import type { ReactNode } from 'react'
import type { LifeEvent } from '../../types'
import { eventWhen, mapPlace } from './todayText'

export function EventItem({ event, children }: { event: LifeEvent; children?: ReactNode }) {
  const label = event.details.label
  return (
    <li className="event">
      <p className="event-when">{eventWhen(event.starts_at, undefined, label ? event.details.timezone : undefined)}{label ? ` · ${label}` : ''}{event.kind === 'plan' ? ' · Plan' : ''}</p>
      <p className="event-summary">{event.summary}{mapPlace(event.details.place) && !event.details.trip && <> <a className="text-button show-on-map" href={`#map/${encodeURIComponent(mapPlace(event.details.place) ?? '')}`}>Show on map</a></>}</p>
      {event.details.post && <p className="event-post">“{event.details.post}”</p>}
      {children}
    </li>
  )
}
