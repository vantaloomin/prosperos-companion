/** Going out with the user and trips away (companion/life/outings.py, trips.py): types and wording for Today and chat. */
import { calendarDay } from '../../when.ts'

export const TOGETHER_KEY = ['outings']

export type OutingState = 'planned' | 'now' | 'done' | 'cancelled'
/** A pastime together (companion/life/hobbies.py) carries the pastime itself under `hobby`. */
export interface OutingHobby { id: string; label: string; session: string; together: string; event: string | null; picture: string }
/** Meeting their people (companion/life/their_people.py): who comes, and whether it is the first time you meet them. */
export interface OutingPerson { id: string; name: string; role: string }
/** A big day in their circle (companion/life/big_days.py): `title` names it ("Leo's wedding"), `gift` is what they bring, and `standing_up` marks their own wedding, where the user stands up with them. */
export interface OutingPlace { id: string; name: string; kind: string; neighborhood: string; summary: string; cost: string; cuisine: string; city: string; hobby?: OutingHobby | null; people?: OutingPerson[]; first?: boolean; big_day?: string; title?: string; event?: string; gift?: string | null; standing_up?: boolean }
export interface Outing {
  id: string; local_date: string; at_time: string; until_time: string; activity: string; asked_date: string | null
  place: OutingPlace; named: boolean; cost: number; cost_text: string; state: OutingState; rolls: number
  ended_at: string | null; undo: boolean
}
/** `visit` marks a weekend visit with the user across the distance (companion/life/long_distance.py): 'to-you' when they come to stay with you, 'host' when you go to stay with them; '' for a trip of their own. `undo` is true for a visit called off a little while ago. */
export interface Trip {
  id: string; start_date: string; end_date: string; city_id: string; city_name: string; kind: 'getaway' | 'family'
  company: { id: string; name: string; role: string } | null; landmark: { name: string; summary: string } | null
  sunny: boolean; cost_text: string; state: OutingState; postcard_message_id: string | null
  visit: '' | 'to-you' | 'host'; undo: boolean
}
export interface Together { outings: Outing[]; trips: Trip[] }

const WHAT: Record<string, string> = {
  dinner: 'Dinner', 'lunch-out': 'Lunch', coffee: 'Coffee', drinks: 'Drinks', show: 'A show', museum: 'A few hours',
  walk: 'A walk', market: 'A look around', 'dinner-in': 'Dinner', hobby: 'A pastime',
  // Visits (companion/life/together.py).
  'visit-in': 'Time together', 'visit-yours': 'A visit', 'dinner-yours': 'Dinner',
  // Meeting their people (companion/life/their_people.py).
  'meet-family': 'Family dinner', 'meet-friends': 'Drinks with friends',
  // Engagement and wedding (companion/life/wedding.py).
  wedding: 'Your wedding',
  // Big days in their circle (companion/life/big_days.py), named by their own title.
  'big-day': 'A big day',
}

/** "Thu, Oct 8" from a local date. */
export function dayText(iso: string): string {
  return calendarDay(iso, { weekday: true })
}

/** "7:00 PM" from "19:00", in the user's own clock style, kept on one line. */
export function timeText(hhmm: string): string {
  const [hours, minutes] = hhmm.split(':').map(Number)
  const text = new Date(Date.UTC(2000, 0, 1, hours, minutes)).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
  // A no-break space, so "7:00" and "PM" never land on different lines.
  return text.replace(/\s/gu, '\u00a0')
}

/** "Dinner at Ouzo Bay". */
export function outingTitle(outing: Pick<Outing, 'activity' | 'place'>): string {
  if (outing.activity === 'hobby' && outing.place.hobby) return `${outing.place.hobby.label} at ${outing.place.name}`
  if (outing.activity === 'big-day' && outing.place.title) return outing.place.title
  if (outing.place.kind === 'your-home') return `${WHAT[outing.activity] ?? 'A visit'} at your place`
  return `${WHAT[outing.activity] ?? 'Out'} at ${outing.place.name}`
}

// A cuisine that already names the kind of place ("irish pub") stands alone.
const PLACE_WORDS = /\b(?:pub|bar|cafe|café|bakery|diner|grill|tavern|bistro|brewery|deli|pizzeria|steakhouse|taqueria|izakaya|trattoria)$/

// Cuisines whose hyphen is part of the name ("Tex-Mex", not "Tex mex").
const JOINED: Record<string, string> = {
  'tex-mex': 'Tex-Mex', 'pan-asian': 'pan-Asian', 'asian-american': 'Asian-American', 'chinese-american': 'Chinese-American',
  'irish-american': 'Irish-American', 'creole-italian': 'Creole-Italian', 'greek-turkish': 'Greek-Turkish', 'latin-asian': 'Latin-Asian',
}

// Their place for dinner or a visit, and the user's own (companion/life/together.py).
const HOMES: Record<string, string> = { home: 'Their place', 'your-home': 'Your place', 'family-home': 'Family home' }

/** "Greek restaurant in Harbor East", "Irish pub in Canton", "Tex-Mex restaurant in Fells Point". */
export function placeLine(place: OutingPlace): string {
  if (place.kind === 'spot') return place.city ? `Somewhere in ${place.city}` : 'Somewhere nearby'
  const home = HOMES[place.kind]
  if (home) return place.neighborhood ? `${home}${place.kind === 'family-home' ? ',' : ' in'} ${place.neighborhood}` : home
  const cuisine = JOINED[place.cuisine] ?? place.cuisine.replace(/-/g, ' ')
  const kind = !cuisine ? place.kind : PLACE_WORDS.test(cuisine) ? cuisine : `${cuisine} ${place.kind}`
  const text = place.neighborhood ? `${kind} in ${place.neighborhood}` : kind
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "With Ana (mom), Rui (dad) and Leo (brother)", for meeting their people; '' for any other outing. Once the evening
 * is over, the first meeting is told as past. */
export function peopleLine(place: OutingPlace, state?: OutingState): string {
  const people = (place.people ?? []).map((person) => `${person.name} (${person.role})`)
  if (!people.length) return ''
  const list = people.length === 1 ? people[0] : `${people.slice(0, -1).join(', ')} and ${people[people.length - 1]}`
  const first = state === 'done' ? ', the first time you met' : ', meeting you for the first time'
  return `With ${list}${place.first ? first : ''}`
}

/** A big day: the user's part in it and the gift. "You're Mira's plus-one. They're bringing a teapot." or, at their
 * own wedding, "You're standing up with Mira."; told as past once it is over. '' for any other outing. */
export function bigDayLine(outing: Pick<Outing, 'activity' | 'place' | 'state'>, name: string): string {
  if (outing.activity !== 'big-day') return ''
  const done = outing.state === 'done'
  const part = outing.place.standing_up
    ? (done ? `You stood up with ${name}.` : `You're standing up with ${name}.`)
    : (done ? `You went as ${name}'s plus-one.` : `You're ${name}'s plus-one.`)
  const gift = outing.place.gift ? ` ${done ? 'They brought' : "They're bringing"} ${outing.place.gift}.` : ''
  return `${part}${gift}`
}

/** When it is, and who picked the place. */
export function outingWhen(outing: Outing, name: string): string {
  const when = `${dayText(outing.local_date)}, ${timeText(outing.at_time)}`
  const moved = outing.asked_date && outing.asked_date !== outing.local_date ? ` (${dayText(outing.asked_date)} didn't work for ${name})` : ''
  return `${when}${moved}`
}

export const OUTING_STATES: Record<OutingState, string> = { planned: 'Coming up', now: 'Out now', done: 'Done', cancelled: 'Called off' }

/** Only what changed from the companion's own pick, and what it cost once it is over. */
export function outingNote(outing: Outing, name: string): string {
  if (outing.state === 'cancelled') return ''
  if (outing.state === 'done') return outing.cost_text ? outing.cost_text.replace(/^You paid/, `${name} paid`) : ''
  if (outing.named) return 'You picked the place.'
  return outing.rolls > 0 ? 'You asked for somewhere else.' : ''
}

/** An item the user just changed, shown collapsed with Undo: "Called off." or "Headed home." */
export function undoText(outing: Outing): string {
  if (!outing.undo) return ''
  return outing.state === 'cancelled' ? 'Called off.' : outing.state === 'done' ? 'Headed home.' : ''
}

/** "Sat, Oct 17 – Sun, Oct 18". */
export function tripDays(trip: Pick<Trip, 'start_date' | 'end_date'>): string {
  return `${dayText(trip.start_date)} – ${dayText(trip.end_date)}`
}

/** "A weekend in New York with Dana", "Visiting Mom in Chicago"; a visit, "Mira comes to stay with you", "You stay with Mira in Chicago". */
export function tripTitle(trip: Trip, name = ''): string {
  if (trip.visit === 'to-you') return `${name} comes to stay with you`
  if (trip.visit === 'host') return `You stay with ${name} in ${trip.city_name}`
  const nights = (Date.parse(trip.end_date) - Date.parse(trip.start_date)) / 86_400_000
  const length = nights >= 2 ? 'A long weekend' : 'A weekend'
  if (trip.kind === 'family' && trip.company) return `Visiting ${trip.company.name} in ${trip.city_name}`
  return `${length} in ${trip.city_name}${trip.company ? ` with ${trip.company.name}` : ''}`
}

/** What Today lists: everything but what was called off, unless it can still be undone. */
export function shown<T extends { state: OutingState; undo?: boolean }>(items: T[]): T[] {
  return items.filter((item) => item.state !== 'cancelled' || item.undo)
}
