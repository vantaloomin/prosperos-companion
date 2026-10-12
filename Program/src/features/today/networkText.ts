import { calendarDay } from '../../when.ts'
import type { Acquaintance, NetworkPerson } from '../../types'

/** "Becca's coworker, 41, nurse": how someone a few layers out is connected, and a little about them. */
export function networkLine(person: Pick<NetworkPerson, 'how' | 'age' | 'occupation'>): string {
  return [person.how, String(person.age), person.occupation].filter(Boolean).join(', ')
}

/** "Met at Becca's Friendsgiving on November 21." */
export function metLine(person: Pick<Acquaintance, 'occasion' | 'met_on'>): string {
  const day = calendarDay(person.met_on, { month: 'long' })
  return `Met at ${person.occasion} on ${day}.`
}
