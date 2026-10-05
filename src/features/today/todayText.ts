import type { PauseRecord, Today } from '../../types'

const time = (value: string, timeZone?: string) => new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone }).format(new Date(value))

/** Routine availability explains a slow or short reply. It never stops the user from writing (PRD C5). */
export function availabilityText(today: Pick<Today, 'availability' | 'companion_timezone'>, name: string): string {
  const { state, label, until } = today.availability
  const end = until ? ` until ${time(until, today.companion_timezone)} their time` : ''
  if (state === 'asleep') return `${name} is asleep${end}. Replies may be slow.`
  if (state === 'working') return `${name} is busy with ${label.toLowerCase() || 'work'}${end}.`
  if (state === 'out') return `${name} is out: ${label.toLowerCase()}${end}.`
  return label ? `${name} is free: ${label.toLowerCase()}.` : `${name} is free.`
}

export function moodText(mood: NonNullable<Today['mood']>, name: string): string {
  const days = Math.round(mood.away_hours / 24)
  const away = days >= 1 ? `${days} day${days === 1 ? '' : 's'}` : `${Math.round(mood.away_hours)} hours`
  return `${name} is in a ${mood.intensity} mood about the ${away} you were apart, from the traits you gave them (${mood.traits.join(', ')}).`
}

/** The most recent finished pause that has not been filled in yet. */
export function pauseToFill(pauses: PauseRecord[]): PauseRecord | null {
  return pauses.find((pause) => pause.ended_at && !pause.catch_up_requested_at) ?? null
}

export function eventWhen(startsAt: string, now = new Date()): string {
  const date = new Date(startsAt)
  const sameDay = date.toDateString() === now.toDateString()
  const day = sameDay ? 'Today' : new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short' }).format(date)
  return `${day}, ${time(startsAt)}`
}

/** A few words for the conversation header. */
export function availabilityShort(availability: Today['availability']): string {
  const label = availability.label.toLowerCase()
  if (availability.state === 'asleep') return 'Asleep'
  if (availability.state === 'working') return label ? `Busy: ${label}` : 'Busy'
  if (availability.state === 'out') return label ? `Out: ${label}` : 'Out'
  return label ? `Free: ${label}` : 'Free'
}
