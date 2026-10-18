import type { CircleChild, CirclePerson } from '../../types'

/** The Growing families slider's steps (companion/life/families.py: PACE, YEARLY and the town's couples.BABY). */
export const FAMILY_LEVELS = [
  { label: 'None', hint: 'Nobody new is expecting. Children already in their lives stay and keep growing up.' },
  { label: 'Now and then', hint: 'Once in a while a sibling, cousin or friend has a baby, and you hear how the little one is getting on.' },
  { label: 'True to life', hint: 'People in their thirties have babies about as often as people do. They become an aunt, uncle or godparent, babysit now and then and go to first birthdays.' },
  { label: 'Lots', hint: 'Babies all round, in their circle and in town, with more updates and more babysitting.' },
]

/** "Mia, 2, Dana's niece" (the companion by first name) or "Leo, 7 months old, Ana's baby": one child under their parent in the people list. */
export function childLine(child: CircleChild, parent: string, companion: string): string {
  const age = child.age_text === 'a newborn' ? 'newborn' : child.age_text
  const whose = child.relation ? `${companion.split(' ')[0]}'s ${child.relation}` : `${parent}'s ${child.pronouns === 'she/her' ? 'daughter' : 'son'}`
  return `${child.name}, ${age}, ${whose}`
}

/** "Baby" until their first birthday, then "Child": the label before a child's line, like the Pet line's. */
export function childLabel(child: CircleChild): string {
  return /^\d+$/.test(child.age_text) ? 'Child' : 'Baby'
}

/** "a baby, due in March", after an "Expecting" label, while they are. */
export function expectingLine(person: CirclePerson): string | null {
  return person.expecting ? `a baby, due in ${person.expecting}` : null
}
