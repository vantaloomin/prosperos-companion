/** The city map (companion/life/citymap.py): types, layout and wording, apart from the drawing for tests. */
import { timeText } from '../today/outingText.ts'

/** `yours` is where the user lives in this world; `known` the home of another companion or of someone in a circle. */
export type Pin = 'home' | 'work' | 'usual' | 'recent' | 'scene' | 'yours' | 'known'
export interface MapPlace {
  id: string; name: string; kind: string; hood: string; hood_id: string; lat: number; lon: number; approx: boolean
  pins: Pin[]; spots: string[]; history: { id: string; summary: string; at: string }[]; regulars: string[]
  /** A home's description, as their Home section has it. */
  about?: string
  /** Their own home's id in their Home section (companion/life/home.py), and whether its rooms were rewritten. */
  item_id?: string; rooms_set?: boolean
  /** Who lives in someone else's home: "Sett's friend", "Another companion". */
  relation?: string
  /** Whether the user rewrote what is inside a place. */
  spots_set?: boolean
  /** Surprise visits (companion/life/drop_by.py), on their home and their work: whether Drop by is on offer now, and
   * the line beside it ("Sett works here. On shift now until 02:00."). */
  drop_by?: DropByOffer
}
export interface MapHood { id: string; name: string; lat: number; lon: number; next: string[] }
/** Sea, a river or a lake from the city data, for the drawn map: a sea by the side the city faces, a river or lake by points. */
export interface MapWater { kind: 'sea' | 'river' | 'lake'; name: string; side: 'north' | 'south' | 'east' | 'west' | null; points: [number, number][]; width_km: number }
export interface CityMapData { city: { id: string; name: string; lat: number; lon: number; real: boolean; enclosed?: boolean }; hoods: MapHood[]; places: MapPlace[]; water?: MapWater[]; story: boolean }

/** Which glyph a place gets: the most telling of its pins, else a plain dot. */
const ORDER: Pin[] = ['scene', 'home', 'yours', 'work', 'usual', 'recent', 'known']
export function mainPin(place: Pick<MapPlace, 'pins'>): Pin | 'place' {
  return ORDER.find((pin) => place.pins.includes(pin)) ?? 'place'
}

export const PIN_LABELS: Record<Pin | 'place', string> = {
  scene: 'Where your story is now', home: 'Their home', yours: 'Your home', known: 'Homes of people they know', work: 'Their work',
  usual: 'Their usual places', recent: 'Places from Feed and Today', place: 'Everywhere else',
}

/** "Coffee after work · Tue" */
export function historyLine(item: { summary: string; at: string }, timeZone?: string): string {
  const day = new Date(item.at).toLocaleDateString(undefined, { weekday: 'short', timeZone })
  const text = item.summary.length > 70 ? `${item.summary.slice(0, 69).trimEnd()}…` : item.summary
  return `${text} · ${day}`
}

/** What the user might send to suggest going together; it goes into the composer, never sent on its own. */
export function suggestion(place: Pick<MapPlace, 'name' | 'kind'> & { id?: string }): string {
  // Their own home: dinner at their place, cooked by them (companion/life/kitchen.py).
  if (place.id === '~home') return 'Can I come over for dinner at your place this week?'
  const when = ['bar', 'nightlife', 'venue', 'restaurant', 'tavern'].includes(place.kind) ? 'one night this week' : 'this weekend'
  return `Want to go to ${place.name} ${when}?`
}

/** Under the invite button: what happens after it, so nobody looks for a way to walk there themselves. */
export function suggestHint(name: string): string {
  return `This puts an invite to ${name} in your chat. If they say yes, it goes on Today. When it's time, you'll be there together. No need to go anywhere.`
}

/** Whether Drop by is on offer, why not when nothing of theirs can be visited now, and at their work the end of the
 * shift they are on ("23:00", null off shift). */
export interface DropByOffer { ok: boolean; note: string; shift_until?: string | null }

/** The line above Drop by: why not ("You're with Sett right now."), or at their work whether they are on shift. */
export function dropByNote(offer: DropByOffer, name: string, work: boolean): string {
  if (offer.note || !work) return offer.note
  return offer.shift_until ? `${name} works here. On shift now until ${timeText(offer.shift_until)}.` : `${name} works here. They're not on shift right now.`
}

/** Drop by's lines: `state` above the button (on shift until when), `under` it what it found once tried, else why it
 * is off right now, else at work that it is a short visit (Iris, 2026-11-03). */
export function dropByLines(offer: DropByOffer, name: string, work: boolean, found: string): { state: string; under: string } {
  const note = dropByNote(offer, name, work)
  if (!offer.ok) return { state: '', under: found || note }
  return { state: note, under: found || (work ? dropByHint(name, true) : '') }
}

/** The button's words, and while it goes. */
export function dropByLabel(work: boolean, going: boolean): string {
  return going ? (work ? 'Heading over…' : 'Knocking…') : 'Drop by'
}

/** Under Drop by: what going unannounced means, at their home or at their work. */
export function dropByHint(name: string, work: boolean): string {
  return work ? `${name} keeps working while you're there, so it's a short visit.`
    : `You go over without asking. ${name} might not be home; if they are, you'll be there together.`
}

/** What dropping by found, from POST /life/drop-by: going in opens the chat, anything else is told on the card. */
export interface DropByResult {
  result: 'in' | 'work' | 'nobody' | 'asleep' | 'not-now'; text: string
  reason?: { why: 'busy' | 'out' | 'away' | 'asleep' | 'plans' | 'late' | 'tense'; label?: string; until?: string } | null
}

/** "Nobody's home. Sett is at work until 11:00 PM.", in the user's own clock style (the server's `text` says 23:00). */
export function dropByFound(found: DropByResult, name: string): string {
  const reason = found.reason
  const until = reason?.until ? timeText(reason.until) : ''
  if (found.result === 'nobody' && reason?.why === 'busy') return `Nobody's home. ${name} is at ${reason.label ?? 'work'} until ${until}.`
  if (found.result === 'nobody' && reason?.why === 'out') return `Nobody's home. ${name} is out until about ${until}.`
  return found.text
}

/** A home rather than a place in the city: theirs, yours, or someone else's ("~home", "~you", "~circle:…"). */
export function isHome(place: Pick<MapPlace, 'id'>): boolean {
  return place.id.startsWith('~')
}

/** "the hearth, the bedroom" from what the user typed, for a home's rooms or a place's spots. */
export function spotList(text: string): string[] {
  return [...new Set(text.split(/[,;\n]/).map((part) => part.trim()).filter(Boolean))].slice(0, 8)
}

/** Places by neighbourhood, for the List view; marked places first in each. */
export function byHood(places: MapPlace[]): [string, MapPlace[]][] {
  const groups = new Map<string, MapPlace[]>()
  for (const place of places) groups.set(place.hood, [...groups.get(place.hood) ?? [], place])
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
    .map(([hood, items]) => [hood, items.sort((a, b) => Number(!a.pins.length) - Number(!b.pins.length) || a.name.localeCompare(b.name))])
}

/** A phone-sized screen, where the place card is a bottom sheet over the lower part of the map. */
export function narrow(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 720px)').matches
}
