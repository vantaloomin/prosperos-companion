/** The city map (companion/life/citymap.py): types, layout and wording, apart from the drawing for tests. */

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
