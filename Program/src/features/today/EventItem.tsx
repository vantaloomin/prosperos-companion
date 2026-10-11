import type { ReactNode } from 'react'
import type { LifeEvent } from '../../types'
import { eventWhen } from './todayText'

export function EventItem({ event, children }: { event: LifeEvent; children?: ReactNode }) {
  const label = event.details.label
  return (
    <li className="event">
      <p className="event-when">{eventWhen(event.starts_at)}{label ? ` · ${label}` : ''}{event.kind === 'plan' ? ' · Plan' : ''}</p>
      <p className="event-summary">{event.summary}{event.details.place?.id && !event.details.trip && <> <a className="text-button show-on-map" href={`#map/${encodeURIComponent(event.details.place.id)}`}>Show on map</a></>}</p>
      {event.details.post && <p className="event-post">“{event.details.post}”</p>}
      {children}
    </li>
  )
}
