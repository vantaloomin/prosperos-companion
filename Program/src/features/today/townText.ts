import type { Townsperson, TownspersonNow } from '../../types'

/** "Bartender at The Claddagh Pub, Canton", "A regular at Patterson Park" or "Electrician, lives in Canton". */
export function townRole(person: Pick<Townsperson, 'role' | 'staff' | 'place' | 'neighborhood'> & { kind?: Townsperson['kind'] }): string {
  if (person.kind === 'resident') return `${person.role.charAt(0).toUpperCase()}${person.role.slice(1)}, lives in ${person.neighborhood}`
  const where = person.neighborhood ? `${person.place.name}, ${person.neighborhood}` : person.place.name
  const role = person.staff ? person.role : 'a regular'
  return `${role.charAt(0).toUpperCase()}${role.slice(1)} at ${where}`
}

/** "Met once, on 5 October" or "Crossed paths 3 times, last on 12 October". */
export function townMet(person: Pick<Townsperson, 'times' | 'last_met'>): string {
  const day = new Date(`${person.last_met}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long' })
  return person.times === 1 ? `Met once, on ${day}.` : `Crossed paths ${person.times} times, last on ${day}.`
}

/** "Probably working as the bartender (upbeat)." for where their rules put them right now. */
export function townNow(now: TownspersonNow): string {
  const where = now.place && !now.doing.includes(now.place.name) ? ` at ${now.place.name}` : ''
  return `Right now: probably ${now.doing}${where} (${now.mood}).`
}
