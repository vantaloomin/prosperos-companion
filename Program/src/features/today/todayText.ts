import { appDate } from '../../appTime.ts'
import type { BodyState, PauseRecord, Recommendation, Today } from '../../types'

const time = (value: string, timeZone?: string) => new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone }).format(new Date(value))

/** Routine availability explains a slow or short reply. It never stops the user from writing (PRD C5). */
export function moodText(mood: NonNullable<Today['mood']>, name: string): string {
  const days = Math.round(mood.away_hours / 24)
  const away = days >= 1 ? `${days} day${days === 1 ? '' : 's'}` : `${Math.round(mood.away_hours)} hours`
  return `${name} is in a ${mood.intensity} mood about the ${away} you were apart, from the traits you gave them (${mood.traits.join(', ')}).`
}

/** The most recent finished pause that has not been filled in yet. */
export function pauseToFill(pauses: PauseRecord[]): PauseRecord | null {
  return pauses.find((pause) => pause.ended_at && !pause.catch_up_requested_at) ?? null
}

/** "Since you were last here" with nothing kept yet: points at what is waiting, if anything is. */
export function changesEmpty(name: string, waiting: number): string {
  if (!waiting) return `Nothing new in ${name}'s life yet. Quiet stretches are normal.`
  const things = waiting === 1 ? '1 thing is' : `${waiting} things are`
  return `${things} waiting for you above. What you keep shows up here.`
}

export function eventWhen(startsAt: string, now = appDate()): string {
  const date = new Date(startsAt)
  const sameDay = date.toDateString() === now.toDateString()
  const day = sameDay ? 'Today' : new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short' }).format(date)
  return `${day}, ${time(startsAt)}`
}

/** A few words for the conversation header. */
/** One line about how the companion feels today, e.g. "Mira is tired, after drinks at the Owl last night." */
export function bodyText(body: BodyState | null | undefined, name: string): string {
  if (!body) return ''
  const feeling = body.state === 'sick' ? 'under the weather' : body.state
  return `${name} is ${feeling}: ${body.because}.`
}

const STARTED: Record<Recommendation['kind'], string> = {
  show: 'watching', movie: 'watching', book: 'reading', music: 'listening', game: 'playing', outing: 'going',
}

/** Where the companion is with something the user recommended. */
export function recommendationText(item: Pick<Recommendation, 'kind' | 'state' | 'verdict'>, name: string): string {
  if (item.state === 'finished') return `${name} finished it and ${item.verdict}.`
  if (item.state === 'started') return `${name} is ${STARTED[item.kind]}, not done yet.`
  return `${name} means to get to it soon.`
}
