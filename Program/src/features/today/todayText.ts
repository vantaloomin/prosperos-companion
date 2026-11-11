import { appDate } from '../../appTime.ts'
import type { BodyState, DayWeather, PauseRecord, Recommendation, Today } from '../../types'

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

/** "18:30" (a clock time of their own day) as the locale writes it: 6:30 PM. */
const clockTime = (at: string) => time(`2000-01-01T${at}:00Z`, 'UTC')

/** When it happens. With `timeZone` (the companion's, beside a label from their day such as "Afternoon") the day
 *  and time are theirs, so the time and the label agree. An outing with the user (`at`, their local "18:30") shows
 *  its own time, not the start of the block it fills (6:00 PM · Evening). */
export function eventWhen(startsAt: string, now = appDate(), timeZone?: string, at?: string): string {
  const date = new Date(startsAt)
  const dayOf = (value: Date) => new Intl.DateTimeFormat('en-CA', { timeZone }).format(value)
  const day = dayOf(date) === dayOf(now) ? 'Today' : new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', timeZone }).format(date)
  return `${day}, ${timeZone && at && /^\d{2}:\d{2}$/.test(at) ? clockTime(at) : time(startsAt, timeZone)}`
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

/** The map place an event's "Show on map" opens, or null for a home that isn't on the map: their place ("~home") or
 * their family's ("~family", companion/life/their_people.py). */
export function mapPlace(place?: { id?: string } | null): string | null {
  return place?.id && !place.id.startsWith('~') ? place.id : null
}

const SKY_WORDS: Record<NonNullable<DayWeather['sky']>, string> = {
  clear: 'Clear', cloudy: 'Some cloud', overcast: 'Overcast', fog: 'Fog', rain: 'Rain', storm: 'Storms', snow: 'Snow',
}

/** "Rain for 3 days, high 48°F": a day's sky (how long a wet or grey spell has held) and its high. A day with no sky
 *  named says wet or dry; a looked-up day says so. `unit` false leaves the unit off ("high 48°"). */
export function dayWeatherText(weather: DayWeather, unit = true): string {
  const sky = weather.sky ? SKY_WORDS[weather.sky] : weather.rain ? 'Rain' : 'Dry'
  return `${sky}${spellText(weather)}, high ${weather.high_f}°${unit ? 'F' : ''}${seenText(weather)}`
}

/** " for 3 days" for a wet or grey spell of two days or more; sunny spells go uncounted. */
function spellText(weather: DayWeather): string {
  const counted = weather.sky && !['clear', 'cloudy'].includes(weather.sky)
  return counted && (weather.days ?? 1) >= 2 ? ` for ${weather.days} days` : ''
}

const seenText = (weather: DayWeather) => (weather.observed ? (weather.observed.forecast ? ' (forecast)' : ' (looked up)') : '')

/** The Now card's weather (Iris, PR #561): on desktop today and tomorrow, the unit said once by the heading's sense,
 *  "Some cloud, high 56° · Tomorrow: some cloud, high 53°"; on phone today only, one line, "Some cloud, high 56°F".
 *  Both empty without weather (a ship has none): the line is left out, never "Unknown". */
export function weatherLine(day: Today['day']): { full: string; short: string } {
  if (!day.weather) return { full: '', short: '' }
  const short = dayWeatherText(day.weather)
  if (!day.tomorrow) return { full: short, short }
  const ahead = dayWeatherText(day.tomorrow, false)
  return { full: `${dayWeatherText(day.weather, false)} · Tomorrow: ${ahead[0].toLowerCase()}${ahead.slice(1)}`, short }
}

/** The summary over a diary line from the companion's own news: "From what Sett said" (Iris, #103). */
export function saidText(companion: string): string {
  const name = companion.trim().split(/\s+/)[0]
  return name ? `From what ${name} said` : 'From what they said'
}
