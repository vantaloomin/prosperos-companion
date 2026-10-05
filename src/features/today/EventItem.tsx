import type { ReactNode } from 'react'
import type { LifeEvent } from '../../types'
import { eventWhen } from './today'

export function EventItem({ event, children }: { event: LifeEvent; children?: ReactNode }) {
  const label = event.details.label
  return (
    <li className="event">
      <p className="event-when">{eventWhen(event.starts_at)}{label ? ` · ${label}` : ''}{event.kind === 'plan' ? ' · Plan' : ''}</p>
      <p className="event-summary">{event.summary}</p>
      {event.details.post && <p className="event-post">“{event.details.post}”</p>}
      {children}
    </li>
  )
}
