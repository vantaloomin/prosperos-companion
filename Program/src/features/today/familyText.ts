/** Wording for a companion's family on Today > People (companion/life/family_circle.py). */
import type { CirclePerson } from '../../types'

/** In the family plan: parents, stepparents and siblings, alive and in touch. */
export const inFamily = (person: CirclePerson) => Boolean(person.kin) && !person.late && !person.estranged

/** Someone of the family they don't talk to anymore (companion/life/family_tree.py). */
export const outOfTouch = (person: CirclePerson) => Boolean(person.estranged) && !person.late

/** "Passed away when Mira was 14." for someone who died before the companion's story began. */
export const longAgoText = (full: string, age: number, companion = full.split(' ')[0]) =>
  age < 1 ? `Passed away before ${companion} was born.` : age < 2 ? `Passed away when ${companion} was a baby.` : `Passed away when ${companion} was ${age}.`

/** "Dana and Jessica don't talk anymore. …", by first names (Iris, family circles 4). */
export const outOfTouchText = (companion: string, name: string) =>
  `${companion.split(' ')[0]} and ${name.split(' ')[0]} don't talk anymore. Restore to bring them back into each other's lives.`

/** "dad · he/him · died at 54": the age they were, not one they are now (Iris, family circles 2). */
export const longAgoFacts = (person: CirclePerson) =>
  [person.role, person.pronouns, person.age ? `died at ${person.age}` : null].filter(Boolean).join(' · ')

export const BRING_BACK_LONG_AGO = (name: string, companion: string) =>
  `${name} is alive, back in ${companion}'s life from today, as if they never passed away.`
