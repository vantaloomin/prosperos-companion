import { calendarDay } from '../../when.ts'
import type { TownLeft, Townsperson, TownspersonNow } from '../../types'

/** "Bartender at The Claddagh Pub, Canton", "A regular at Patterson Park" or "Electrician, lives in Canton". */
export function townRole(person: Pick<Townsperson, 'role' | 'staff' | 'place' | 'neighborhood'> & { kind?: Townsperson['kind']; left?: TownLeft | null }): string {
  const gone = !!person.left
  if (person.kind === 'resident') return `${person.role.charAt(0).toUpperCase()}${person.role.slice(1)}, ${gone ? 'used to live' : 'lives'} in ${person.neighborhood}`
  const where = person.neighborhood ? `${person.place.name}, ${person.neighborhood}` : person.place.name
  const role = person.staff ? person.role : 'a regular'
  // Someone who left (companion/world/turnover.py) is spoken of in the past: "Formerly docent at Walters Art Museum".
  return gone ? `Formerly ${role} at ${where}` : `${role.charAt(0).toUpperCase()}${role.slice(1)} at ${where}`
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

/** "Moved away for a new job (June 2027).", "Moved away (December 2027).", "Retired (February 2040)." or
 * "Passed away (January 2040)." for someone who has left town (companion/world/turnover.py). */
export function townLeft(left: TownLeft): string {
  const [year, month] = left.day.split('-').map(Number)
  const when = new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' })
  const what = { moved: 'Moved away', 'new job': 'Moved away for a new job', retired: 'Retired', passed: 'Passed away' }[left.why]
  return `${what} (${when}).`
}

/** A job in the past tense for someone who left: "Formerly a librarian" from "Librarian at Enoch Pratt". */
export function formerly(job: string): string {
  const role = job.split(' at ')[0].trim().toLowerCase()
  return role ? `Formerly ${/^[aeiou]/.test(role) ? 'an' : 'a'} ${role}` : 'Formerly in town'
}
