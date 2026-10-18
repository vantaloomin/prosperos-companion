import { calendarDay } from '../../when.ts'
import type { TownLeft, Townsperson, TownspersonNow } from '../../types'

/** "Bartender at The Claddagh Pub, Canton", "A regular at Patterson Park" or "Electrician, lives in Canton". */
export function townRole(person: Pick<Townsperson, 'role' | 'staff' | 'place' | 'neighborhood'> & { kind?: Townsperson['kind'] }): string {
  if (person.kind === 'resident') return `${person.role.charAt(0).toUpperCase()}${person.role.slice(1)}, lives in ${person.neighborhood}`
  const where = person.neighborhood ? `${person.place.name}, ${person.neighborhood}` : person.place.name
  const role = person.staff ? person.role : 'a regular'
  return `${role.charAt(0).toUpperCase()}${role.slice(1)} at ${where}`
}

/** "Met once, on October 5" or "Crossed paths 3 times, last on October 12". */
export function townMet(person: Pick<Townsperson, 'times' | 'last_met'>): string {
  const day = calendarDay(person.last_met, { month: 'long' })
  return person.times === 1 ? `Met once, on ${day}.` : `Crossed paths ${person.times} times, last on ${day}.`
}

/** "Probably working as the bartender (upbeat)." for where their rules put them right now. */
export function townNow(now: TownspersonNow): string {
  const where = now.place && !now.doing.includes(now.place.name) ? ` at ${now.place.name}` : ''
  return `Right now: probably ${now.doing}${where} (${now.mood}).`
}

/** "Has since moved away (June 2027)." or "Passed away in June 2027." */
export function townLeft(left: TownLeft): string {
  const [year, month] = left.day.split('-').map(Number)
  const when = new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' })
  return left.why === 'passed' ? `Passed away in ${when}.` : `Has since ${left.text} (${when}).`
}
