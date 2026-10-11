/** Going out with the user and trips away (companion/life/outings.py, trips.py): types and wording for Today and chat. */

export const TOGETHER_KEY = ['outings']

export type OutingState = 'planned' | 'now' | 'done' | 'cancelled'
export interface OutingPlace { id: string; name: string; kind: string; neighborhood: string; summary: string; cost: string; cuisine: string; city: string }
export interface Outing {
  id: string; local_date: string; at_time: string; until_time: string; activity: string; asked_date: string | null
  place: OutingPlace; named: boolean; cost: number; cost_text: string; state: OutingState; rolls: number
  ended_at: string | null; undo: boolean
}
export interface Trip {
  id: string; start_date: string; end_date: string; city_id: string; city_name: string; kind: 'getaway' | 'family'
  company: { id: string; name: string; role: string } | null; landmark: { name: string; summary: string } | null
  sunny: boolean; cost_text: string; state: OutingState; postcard_message_id: string | null
}
export interface Together { outings: Outing[]; trips: Trip[] }

const WHAT: Record<string, string> = {
  dinner: 'Dinner', 'lunch-out': 'Lunch', coffee: 'Coffee', drinks: 'Drinks', show: 'A show', museum: 'A few hours',
  walk: 'A walk', market: 'A look round',
}

/** "Thu, Oct 8" from a local date. */
export function dayText(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' })
}

/** "7:00 PM" from "19:00", in the user's own clock style. */
export function timeText(hhmm: string): string {
  const [hours, minutes] = hhmm.split(':').map(Number)
  return new Date(Date.UTC(2000, 0, 1, hours, minutes)).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
}

/** "Dinner at Ouzo Bay". */
export function outingTitle(outing: Pick<Outing, 'activity' | 'place'>): string {
  return `${WHAT[outing.activity] ?? 'Out'} at ${outing.place.name}`
}

// A cuisine that already names the kind of place ("irish pub") stands alone.
const PLACE_WORDS = /\b(?:pub|bar|cafe|café|bakery|diner|grill|tavern|bistro|brewery|deli|pizzeria|steakhouse|taqueria|izakaya|trattoria)$/

/** "Greek restaurant in Harbor East", "Irish pub in Canton". */
export function placeLine(place: OutingPlace): string {
  const cuisine = place.cuisine.replace(/-/g, ' ')
  const kind = !cuisine ? place.kind : PLACE_WORDS.test(cuisine) ? cuisine : `${cuisine} ${place.kind}`
  const text = place.neighborhood ? `${kind} in ${place.neighborhood}` : kind
  return text.charAt(0).toUpperCase() + text.slice(1)
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

/** "A weekend in New York with Dana", "Visiting Mom in Chicago". */
export function tripTitle(trip: Trip): string {
  const nights = (Date.parse(trip.end_date) - Date.parse(trip.start_date)) / 86_400_000
  const length = nights >= 2 ? 'A long weekend' : 'A weekend'
  if (trip.kind === 'family' && trip.company) return `Visiting ${trip.company.name} in ${trip.city_name}`
  return `${length} in ${trip.city_name}${trip.company ? ` with ${trip.company.name}` : ''}`
}

/** The chat strip while an outing is under way: "Out with Mira at Ouzo Bay until 9:00 PM". */
export function outNowText(outing: Outing, name: string): string {
  return `Out with ${name} at ${outing.place.name} until ${timeText(outing.until_time)}`
}

/** The outing under way, or one the user just headed home from (still undoable). */
export function outNow(data: Together | undefined): Outing | null {
  return data?.outings.find((outing) => outing.state === 'now' || (outing.state === 'done' && outing.undo)) ?? null
}

/** What Today lists: everything but what was called off, unless it can still be undone. */
export function shown<T extends { state: OutingState; undo?: boolean }>(items: T[]): T[] {
  return items.filter((item) => item.state !== 'cancelled' || item.undo)
}
