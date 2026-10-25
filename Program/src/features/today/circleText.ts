import type { CirclePerson } from '../../types'

/** "close friend · she/her · 40" or "sister · married, born Smith · she/her · 31": how they relate to the companion, then what is known about them. */
export function personFacts(person: CirclePerson): string {
  const role = person.closeness && person.closeness !== 'close' ? `${person.role} (${person.closeness})` : person.role
  const married = person.married ? (person.birth_family ? `married, born ${person.birth_family}` : 'married') : null
  return [role, married, person.pronouns, person.age ? String(person.age) : null].filter(Boolean).join(' · ')
}

/** Where they are in their week, without implying the companion is with them. */
export function personNow(person: CirclePerson): string {
  if (person.local === false) return 'Lives out of town'
  if (person.met?.meeting === 'now') return 'Right now: meeting you'
  if (!person.now) return 'Free right now'
  return person.now.kind === 'sleep' ? 'Asleep right now' : `Right now: ${person.now.label}`
}

export function personWork(person: CirclePerson): string | null {
  if (!person.career) return null
  return person.employer ? `${person.career}, ${person.employer}` : person.career
}

/** The full name when known (it tells apart two people with one given name), unless they were renamed since. */
export function displayName(person: CirclePerson): string {
  return person.full_name?.startsWith(`${person.name} `) ? person.full_name : person.name
}

/** Parents in the circle: married, divorced, or separated in an older city (companion/life/circle.py `tie`). */
const COUPLED: Record<string, string> = { married: 'Married to', divorced: 'Divorced from', separated: 'Separated from' }

/** "Married to Rui. Knows Ana (family), Dev (coworkers)": who they know inside the circle. */
export function personTies(person: CirclePerson): string | null {
  const known = person.knows ?? []
  const partners = known.filter((item) => Object.hasOwn(COUPLED, item.how))
    .map((item) => `${COUPLED[item.how]} ${item.name}.`)
  const others = known.filter((item) => !Object.hasOwn(COUPLED, item.how)).map((item) => `${item.name} (${item.how})`)
  const text = [...partners, ...(others.length ? [`Knows ${others.join(', ')}.`] : [])].join(' ')
  return text || null
}

/** "Met you Oct 17, 2026 · Liked you right away", "Knows you from way back · Warmed to you", or "Meeting you soon"
 * (companion/life/their_people.py). What they think stays unsaid until they have met you. */
export function metText(person: CirclePerson): string | null {
  const met = person.met
  if (!met) return null
  if (met.meeting) return met.meeting === 'now' ? 'Meeting you now' : 'Meeting you soon'
  return `${met.before ? 'Knows you from way back' : `Met you ${shortDate(met.met_on ?? '')}`} · ${met.label}`
}

/** "Oct 17", kept on one line. */
function shortDate(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }).replace(/ /g, '\u00a0')
}

/** What someone in the circle can be to the companion, offered while typing (any other words work too). */
export const RELATION_WORDS = ['friend', 'close friend', 'best friend', 'mom', 'dad', 'sister', 'brother', 'cousin', 'aunt', 'uncle',
  'grandmother', 'grandfather', 'partner', 'roommate', 'neighbor', 'coworker', 'boss', 'mentor', 'old friend from school']

/** The form's fields as text, the way the inputs hold them. */
export interface AboutValues { name: string; role: string; pronouns: string; job: string; employer: string; age: string; local: 'here' | 'away'; note: string }

/** Ages the picker offers: 16 to 110, and their own when it is outside that (an elf of 300). */
export function AGE_CHOICES(current: string): string[] {
  const ages = Array.from({ length: 95 }, (_, index) => String(index + 16))
  return current && !ages.includes(current) ? [...ages, current].sort((a, b) => Number(a) - Number(b)) : ages
}

/** The form for someone in the circle, filled in from them, or empty for someone new. */
export function aboutForm(person?: CirclePerson) {
  const values = person ? aboutValues(person) : EMPTY_ABOUT
  return { values, submit: person ? 'Save' : 'Add', title: (companion: string) => person ? `Change ${person.name}` : `Add someone to ${companion}'s life` }
}

const EMPTY_ABOUT: AboutValues = { name: '', role: '', pronouns: '', job: '', employer: '', age: '', local: 'here', note: '' }

function aboutValues(person: CirclePerson): AboutValues {
  return {
    name: displayName(person), role: person.role, pronouns: person.pronouns ?? '',
    // A coworker's "Works with Dana" is how the card says it, not a job to edit.
    job: person.works_with_companion ? '' : person.career ?? '', employer: person.employer ?? '',
    age: typeof person.age === 'number' ? String(person.age) : '', local: person.local === false ? 'away' : 'here', note: person.note ?? '',
  }
}

const ABOUT_TEXT = ['name', 'role', 'job', 'employer', 'note'] as const
type AboutChange = Record<string, string | number | boolean>

/** What the server is sent: everything filled in for someone new, only what changed for someone already there. */
export function aboutChange(before: AboutValues, after: AboutValues, adding: boolean): AboutChange {
  return adding ? newPerson(after) : changedPerson(before, after)
}

function newPerson(after: AboutValues): AboutChange {
  const change: AboutChange = {}
  for (const key of ABOUT_TEXT) if (after[key].trim()) change[key] = after[key].trim()
  if (after.pronouns) change.pronouns = after.pronouns
  if (after.age) change.age = Number(after.age)
  if (after.local === 'away') change.local = false
  return change
}

function changedPerson(before: AboutValues, after: AboutValues): AboutChange {
  const change: AboutChange = {}
  for (const key of ABOUT_TEXT) if (after[key].trim() !== before[key].trim()) change[key] = after[key].trim()
  // A name and who they are can't be emptied; the rest can (an empty job is no job).
  if (change.name === '') delete change.name
  if (change.role === '') delete change.role
  if (after.pronouns !== before.pronouns) change.pronouns = after.pronouns
  if (after.age !== before.age) change.age = Number(after.age)
  if (after.local !== before.local) change.local = after.local === 'here'
  return change
}

/** The confirmation once saved. */
export function aboutSaved(person: CirclePerson | undefined, name: string, companion: string): string {
  if (!person) return `${name} is now part of ${companion}'s life.`
  return `Saved ${name || person.name}. Moments that already happened keep what they said.`
}
