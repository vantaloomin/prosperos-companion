import type { CircleChild, CirclePerson } from '../../types'

/** The Growing families slider's steps (companion/life/families.py: PACE, YEARLY and the town's couples.BABY). */
export const FAMILY_LEVELS = [
  { label: 'None', hint: 'Nobody new is expecting, and new companions and their new partners come without kids unless a description names some. Children already in their lives stay and keep growing up.' },
  { label: 'Now and then', hint: 'Once in a while a sibling, cousin or friend has a baby, and you hear how the little one is getting on.' },
  { label: 'True to life', hint: 'People in their thirties have babies about as often as people do. They become an aunt, uncle or godparent, babysit now and then and go to first birthdays. Living with a partner, they may start a family of their own.' },
  { label: 'Lots', hint: 'Babies all round, in their circle and in town, with more updates and more babysitting.' },
]

/** The Family life slider's steps (companion/life/our_child.py: BROKEN, SICK_DAYS and SLEEPS), for the pair's own
 * children. */
export const FAMILY_LIFE_LEVELS = [
  { label: 'Easy', hint: 'Only the good days: no broken nights or sick days, and babies sleep through early. Milestones, days out and holidays all still come.' },
  { label: 'Gentle', hint: 'Now and then a broken night or a day off with a sick child; most days run smoothly.' },
  { label: 'True to life', hint: 'Months of broken nights, a few sick days off work a year, bedtimes, the school run and childcare to pay for.' },
  { label: 'Chaotic', hint: 'Long months of broken nights, more sick days, and babies who sleep through late.' },
]

/** "Mia, 2, Dana's niece" (the companion by first name), "Leo, 7 months old, Ana's son", or the companion's own
 * with their partner: "Ivy, newborn, Dana and Tyler's daughter". One child under their parent in the people list. */
export function childLine(child: CircleChild, parent: string, companion: string): string {
  const age = child.age_text === 'a newborn' ? 'newborn' : child.age_text
  const first = companion.split(' ')[0]
  const whose = child.own ? `${first} and ${parent.split(' ')[0]}'s ${child.relation}`
    : child.relation ? `${first}'s ${child.relation}` : `${parent}'s ${child.pronouns === 'she/her' ? 'daughter' : 'son'}`
  return `${child.name}, ${age}, ${whose}`
}

/** "Baby" until their first birthday, then "Child": the label before a child's line, like the Pet line's. */
export function childLabel(child: CircleChild): string {
  return /^\d+$/.test(child.age_text) ? 'Child' : 'Baby'
}

/** "a baby, due in March" after an "Expecting" label, or "a baby, coming home around March" after "Adopting". */
export function expectingLine(person: CirclePerson): string | null {
  if (!person.expecting) return null
  return person.adopting ? `a baby, coming home around ${person.expecting}` : `a baby, due in ${person.expecting}`
}

/** "Expecting" or, for the companion and their partner adopting, "Adopting". */
export function expectingLabel(person: CirclePerson): string {
  return person.adopting ? 'Adopting' : 'Expecting'
}
