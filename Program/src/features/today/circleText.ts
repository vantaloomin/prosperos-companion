import type { CircleHome, CirclePerson } from '../../types'

type Aboard = CircleHome['aboard']

/** What "where they live" says: in and out of town, or aboard and off a ship or station. */
export function placeWords(aboard: Aboard = null): { here: string; away: string } {
  if (aboard === 'station') return { here: 'On the station', away: 'Off the station' }
  if (aboard === 'ship') return { here: 'Aboard the ship', away: 'Off the ship' }
  return { here: 'In town', away: 'Out of town' }
}

/** "close friend · she/her · 40" or "sister · married, born Smith · she/her · 31": how they relate to the companion, then what is known about them. */
export function personFacts(person: CirclePerson): string {
  const role = person.closeness && person.closeness !== 'close' ? `${person.role} (${person.closeness})` : person.role
  const married = person.married ? (person.birth_family ? `married, born ${person.birth_family}` : 'married') : null
  return [role, married, person.pronouns, person.age ? String(person.age) : null].filter(Boolean).join(' · ')
}

/** Where they are in their week, without implying the companion is with them. */
export function personNow(person: CirclePerson, aboard: Aboard = null): string {
  if (person.local === false) return `Lives ${placeWords(aboard).away.toLowerCase()}`
  if (person.met?.meeting === 'now') return 'Right now: meeting you'
  if (!person.now) return 'Free right now'
  return person.now.kind === 'sleep' ? 'Asleep right now' : `Right now: ${person.now.label}`
}

export function personWork(person: CirclePerson): string | null {
  if (!person.career) return person.employer ? `Works at ${person.employer}` : null
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
export interface AboutValues { name: string; role: string; pronouns: string; job: string; employer: string; age: string; local: '' | 'here' | 'away'; note: string; start: string }

export const NOTE_MAX = 300
const AGES = { least: 16, most: 120 }

/** An age typed in the box, kept in range when the box is left: their own age may be past the usual most (an elf of
 * 300), and the box says what it kept. */
export function ageClamp(value: string, current: string): { value: string; note: string } {
  if (!value) return { value, note: '' }
  const most = Math.max(AGES.most, Number(current) || 0)
  const age = Number(value)
  if (age > most) return { value: String(most), note: `Kept at ${most}, the most.` }
  if (age < AGES.least) return { value: String(AGES.least), note: `Kept at ${AGES.least}, the least.` }
  return { value: String(age), note: '' }
}

/** "260 of 300" once the note nears its limit, else nothing. */
export function noteCount(note: string): string {
  return note.length >= NOTE_MAX - 60 ? `${note.length} of ${NOTE_MAX}` : ''
}

/** The form for someone in the circle, filled in from them, or empty for someone new. */
export function aboutForm(person?: CirclePerson) {
  const values = person ? aboutValues(person) : EMPTY_ABOUT
  return { values, submit: person ? 'Save' : 'Add', title: (companion: string) => person ? `Change ${person.name}` : `Add someone to ${companion}'s life` }
}

const EMPTY_ABOUT: AboutValues = { name: '', role: '', pronouns: '', job: '', employer: '', age: '', local: '', note: '', start: '' }

function aboutValues(person: CirclePerson): AboutValues {
  return {
    name: displayName(person), role: person.role, pronouns: person.pronouns ?? '',
    // A coworker's "Works with Dana" is how the card says it, not a job to edit.
    job: person.works_with_companion ? '' : person.career ?? '', employer: person.employer ?? '',
    age: typeof person.age === 'number' ? String(person.age) : '', local: person.local === false ? 'away' : 'here', note: person.note ?? '',
    start: person.start_stage ? String(person.start_stage) : '',
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
  if (after.local) change.local = after.local === 'here'
  if (after.start) change.start_stage = Number(after.start)
  return change
}

function changedPerson(before: AboutValues, after: AboutValues): AboutChange {
  const change: AboutChange = {}
  for (const key of ABOUT_TEXT) if (after[key].trim() !== before[key].trim()) change[key] = after[key].trim()
  // A name and who they are can't be emptied; the rest can (an empty job is no job).
  if (change.name === '') delete change.name
  if (change.role === '') delete change.role
  if (after.pronouns !== before.pronouns) change.pronouns = after.pronouns
  if (after.age && after.age !== before.age) change.age = Number(after.age)
  if (after.local !== before.local) change.local = after.local === 'here'
  return { ...change, ...changedStart(before, after) }
}

/** Where they start with the companion; back to the app's pick is 0. */
function changedStart(before: AboutValues, after: AboutValues): AboutChange {
  return after.start === before.start ? {} : { start_stage: Number(after.start || 0) }
}

/** The confirmation once saved. */
export function aboutSaved(person: CirclePerson | undefined, name: string, companion: string): string {
  if (!person) return `${name} is now part of ${companion}'s life.`
  return `Saved ${name || person.name}. Moments that already happened stay as they were.`
}

/** How two people in the circle can know each other, as the user picks it (companion/life/circle.py TIE_WORDS). */
export const TIE_CHOICES: { value: string; label: string }[] = [
  { value: 'friends', label: 'Friends' }, { value: 'old friends', label: 'Old friends' }, { value: 'family', label: 'Family' },
  { value: 'coworkers', label: 'Coworkers' }, { value: 'known for years', label: 'Known for years' }, { value: 'rivals', label: 'Rivals' },
  { value: 'married', label: 'Married' }, { value: 'divorced', label: 'Divorced' }, { value: 'separated', label: 'Separated' },
]
