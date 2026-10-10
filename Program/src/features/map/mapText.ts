/** The city map (companion/life/citymap.py): types, layout and wording, apart from the drawing for tests. */

export type Pin = 'home' | 'work' | 'usual' | 'recent' | 'scene'
export interface MapPlace {
  id: string; name: string; kind: string; hood: string; hood_id: string; lat: number; lon: number; approx: boolean
  pins: Pin[]; spots: string[]; history: { id: string; summary: string; at: string }[]; regulars: string[]
}
export interface MapHood { id: string; name: string; lat: number; lon: number; next: string[] }
export interface CityMapData { city: { id: string; name: string; lat: number; lon: number; real: boolean }; hoods: MapHood[]; places: MapPlace[]; story: boolean }

/** Which glyph a place gets: the most telling of its pins, else a plain dot. */
const ORDER: Pin[] = ['scene', 'home', 'work', 'usual', 'recent']
export function mainPin(place: Pick<MapPlace, 'pins'>): Pin | 'place' {
  return ORDER.find((pin) => place.pins.includes(pin)) ?? 'place'
}

export const PIN_LABELS: Record<Pin | 'place', string> = {
  scene: 'Where your story is now', home: 'Their home', work: 'Their work', usual: 'Their usual places', recent: 'Places from Feed and Today', place: 'Everywhere else',
}

/** "Coffee after work · Tue" */
export function historyLine(item: { summary: string; at: string }, timeZone?: string): string {
  const day = new Date(item.at).toLocaleDateString('en-US', { weekday: 'short', timeZone })
  const text = item.summary.length > 70 ? `${item.summary.slice(0, 69).trimEnd()}…` : item.summary
  return `${text} · ${day}`
}

/** What the user might send to suggest going together; it goes into the composer, never sent on its own. */
export function suggestion(place: Pick<MapPlace, 'name' | 'kind'>): string {
  const when = ['bar', 'nightlife', 'venue', 'restaurant', 'tavern'].includes(place.kind) ? 'one night this week' : 'this weekend'
  return `Want to go to ${place.name} ${when}?`
}

/** Places by neighbourhood, for the List view; marked places first in each. */
export function byHood(places: MapPlace[]): [string, MapPlace[]][] {
  const groups = new Map<string, MapPlace[]>()
  for (const place of places) groups.set(place.hood, [...groups.get(place.hood) ?? [], place])
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
    .map(([hood, items]) => [hood, items.sort((a, b) => Number(!a.pins.length) - Number(!b.pins.length) || a.name.localeCompare(b.name))])
}

export interface Bubble { id: string; name: string; x: number; y: number; r: number; places: { place: MapPlace; x: number; y: number }[] }
const GAP = 16

/**
 * The sketch map's layout: each neighbourhood a round shape where the city data puts it, pushed apart until
 * none overlap, with its places in a loose grid inside. Not to scale, and it says so.
 */
export function sketch(data: CityMapData): { bubbles: Bubble[]; width: number; height: number } {
  if (!data.hoods.length) return { bubbles: [], width: 400, height: 300 }
  const squash = Math.cos((data.city.lat * Math.PI) / 180)
  const xs = data.hoods.map((hood) => hood.lon * squash), ys = data.hoods.map((hood) => hood.lat)
  const scale = 900 / Math.max(Math.max(...xs) - Math.min(...xs) || 1, Math.max(...ys) - Math.min(...ys) || 1)
  const bubbles: Bubble[] = data.hoods.map((hood) => {
    const count = data.places.filter((place) => place.hood_id === hood.id).length
    const r = Math.max(46, (Math.ceil(Math.sqrt(count)) * GAP) / 1.25 + 22)
    return { id: hood.id, name: hood.name, x: (hood.lon * squash - Math.min(...xs)) * scale, y: (Math.max(...ys) - hood.lat) * scale, r, places: [] }
  })
  separate(bubbles)
  const left = Math.min(...bubbles.map((bubble) => bubble.x - bubble.r)) - 40, top = Math.min(...bubbles.map((bubble) => bubble.y - bubble.r)) - 60
  for (const bubble of bubbles) {
    bubble.x -= left; bubble.y -= top
    bubble.places = grid(bubble, data.places.filter((place) => place.hood_id === bubble.id))
  }
  return { bubbles, width: Math.max(...bubbles.map((bubble) => bubble.x + bubble.r)) + 40, height: Math.max(...bubbles.map((bubble) => bubble.y + bubble.r)) + 40 }
}

/** Pushes overlapping neighbourhoods apart until each has room. */
function separate(bubbles: Bubble[]) {
  for (let round = 0; round < 200; round++) {
    let moved = false
    for (const a of bubbles) for (const b of bubbles) if (a !== b && pushApart(a, b)) moved = true
    if (!moved) return
  }
}

function pushApart(a: Bubble, b: Bubble): boolean {
  const dx = b.x - a.x || 0.1, dy = b.y - a.y || 0.1, distance = Math.hypot(dx, dy), need = a.r + b.r + 18
  if (distance >= need) return false
  const push = (need - distance) / 2
  a.x -= (dx / distance) * push; a.y -= (dy / distance) * push
  b.x += (dx / distance) * push; b.y += (dy / distance) * push
  return true
}

function grid(bubble: Bubble, places: MapPlace[]): Bubble['places'] {
  const columns = Math.max(1, Math.ceil(Math.sqrt(places.length)))
  const rows = Math.ceil(places.length / columns)
  return places.map((place, index) => ({
    place, x: bubble.x + ((index % columns) - (columns - 1) / 2) * GAP, y: bubble.y + 10 + (Math.floor(index / columns) - (rows - 1) / 2) * GAP,
  }))
}

/** Each pair of neighbouring neighbourhoods once, for the sketch's dotted lines. */
export function pairs(hoods: MapHood[]): [string, string][] {
  const seen = new Set<string>()
  const found: [string, string][] = []
  for (const hood of hoods) for (const other of hood.next) {
    const key = [hood.id, other].sort().join('|')
    if (!seen.has(key)) { seen.add(key); found.push([hood.id, other]) }
  }
  return found
}
