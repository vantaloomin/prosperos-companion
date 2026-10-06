import type { Acquaintance, NetworkPerson } from '../../types'

/** "Becca's coworker, 41, nurse": how someone a few layers out is connected, and a little about them. */
export function networkLine(person: Pick<NetworkPerson, 'how' | 'age' | 'occupation'>): string {
  return [person.how, String(person.age), person.occupation].filter(Boolean).join(', ')
}

/** "Met at Becca's Friendsgiving on 21 November." */
export function metLine(person: Pick<Acquaintance, 'occasion' | 'met_on'>): string {
  const day = new Date(`${person.met_on}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long' })
  return `Met at ${person.occasion} on ${day}.`
}
