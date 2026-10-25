/** Prospero's Draft Table (companion/world/draft): the draft's shape and the pure edits on it, tested directly. */
import { unit } from '../map/drawn.ts'
import type { CityMapData, MapPlace } from '../map/mapText.ts'
import { slugify, type CityListing } from '../world/cityText.ts'

export interface Item { id: string; name: string; summary: string; neighborhood?: string | null; kind?: string; [key: string]: unknown }
export interface Hood extends Item { lat: number; lon: number; transit?: string[] }
export interface Hub extends Item { neighborhoods: string[] }
export interface Colour extends Item { places?: string[] }
export interface Definition {
  id: string; name: string; summary: string; region: string; country: string; era: string; lat: number; lon: number
  neighborhoods: Hood[]; places: Item[]; employers: Item[]; career_hubs: Hub[]; colleges?: Item[]; transit: Item[]
  annual_events: (Item & { months: number[] })[]; local_color: Colour[]; enclosed?: boolean; water?: CityMapData['water']
  [key: string]: unknown
}
/** How the line was read (companion/world/draft/brief.py). */
export interface Brief { line: string; era: string; group: string; aboard: boolean; water: string | null; biome: string; size: string; year: number | null; name: string | null; anchor: string; donor: string }
export interface Checked { summary: CityListing; notes: string[]; warnings: string[] }
export interface Drafted extends Checked { definition: Definition; brief: Brief }

export const SECTIONS = ['name', 'hoods', 'places', 'employers', 'transit', 'events', 'colour'] as const
export type Section = typeof SECTIONS[number]
export type Rolls = Partial<Record<Section, number>>

/** Everything open on the table, kept on this device between visits. A city file opened on the table has no brief,
 * so nothing to redraw from. `saved` is the city it was saved as. Until the user types in the place's summary
 * (`summaryEdited`), it is written again after every change; `gone` names the parts removed since, which a summary
 * they wrote may still mention. */
export interface Work {
  line: string; seed: string; rolls: Rolls; definition: Definition; brief: Brief | null; edited: boolean
  saved?: { id: string; revision: number }; summaryEdited?: boolean; gone?: string[]
}

/** The lists the table edits, by the key they have in the city file. */
export type ListKey = 'neighborhoods' | 'places' | 'employers' | 'transit' | 'annual_events' | 'local_color'

/** What redrawing a section replaces. The name and the neighbourhoods carry everything else, so they redraw the lot. */
const REDRAWS: Partial<Record<Section, (keyof Definition)[]>> = {
  places: ['places'], employers: ['employers', 'career_hubs'], transit: ['transit', 'speeds'],
  events: ['annual_events'], colour: ['local_color'],
}

export function redrawsAll(section: Section): boolean {
  return !REDRAWS[section]
}

export function newSeed(): string {
  return Math.floor(Math.random() * 1e9).toString(36)
}

/** A section from a fresh build put into the draft, keeping every edit elsewhere and dropping what points at
 * something the user has since removed. */
export function takeSection(current: Definition, fresh: Definition, section: Section): Definition {
  const keys = REDRAWS[section]
  if (!keys) return fresh
  const next: Definition = { ...current }
  for (const key of keys) next[key] = structuredClone(fresh[key])
  const hoods = new Set(current.neighborhoods.map((hood) => hood.id))
  next.places = next.places.filter((item) => hoods.has(item.neighborhood ?? ''))
  next.employers = next.employers.filter((item) => hoods.has(item.neighborhood ?? ''))
  next.career_hubs = next.career_hubs.map((hub) => ({ ...hub, neighborhoods: hub.neighborhoods.filter((id) => hoods.has(id)) }))
    .filter((hub) => hub.neighborhoods.length)
  next.annual_events = next.annual_events.map((item) => hoods.has(item.neighborhood ?? '') ? item : withoutHood(item))
  if (section === 'transit') {
    const lines = new Map(fresh.neighborhoods.map((hood) => [hood.id, hood.transit ?? []]))
    next.neighborhoods = current.neighborhoods.map((hood) => lines.has(hood.id) ? { ...hood, transit: lines.get(hood.id) } : hood)
  }
  return tidy(next)
}

function withoutHood<T extends Item>(item: T): T {
  const copy = { ...item }
  delete copy.neighborhood
  return copy
}

/** Local colour names places, and neighbourhoods name ways to get about: keep only the ones still there. */
function tidy(definition: Definition): Definition {
  const places = new Set(definition.places.map((item) => item.id))
  const lines = new Set(definition.transit.map((item) => item.id))
  return {
    ...definition,
    local_color: definition.local_color.map((item) => item.places?.some((id) => !places.has(id)) ? { ...item, places: item.places.filter((id) => places.has(id)) } : item),
    neighborhoods: definition.neighborhoods.map((hood) => hood.transit?.some((id) => !lines.has(id)) ? { ...hood, transit: hood.transit.filter((id) => lines.has(id)) } : hood),
  }
}

/** What else goes with a neighbourhood when it is removed, for the question before it goes. */
export function inHood(definition: Definition, id: string) {
  return { places: definition.places.filter((item) => item.neighborhood === id).length, employers: definition.employers.filter((item) => item.neighborhood === id).length }
}

export function removeItem(definition: Definition, key: ListKey, id: string): Definition {
  const next = { ...definition, [key]: (definition[key] as Item[]).filter((item) => item.id !== id) } as Definition
  if (key === 'neighborhoods') {
    next.places = next.places.filter((item) => item.neighborhood !== id)
    next.employers = next.employers.filter((item) => item.neighborhood !== id)
    next.colleges = next.colleges?.filter((item) => item.neighborhood !== id)
    next.career_hubs = next.career_hubs.map((hub) => ({ ...hub, neighborhoods: hub.neighborhoods.filter((hood) => hood !== id) })).filter((hub) => hub.neighborhoods.length)
    next.annual_events = next.annual_events.map((item) => item.neighborhood === id ? withoutHood(item) : item)
  }
  return tidy(next)
}

export function changeItem(definition: Definition, key: ListKey, id: string, change: Partial<Item>): Definition {
  return { ...definition, [key]: (definition[key] as Item[]).map((item) => item.id === id ? { ...item, ...change } : item) } as Definition
}

/** The city's own name and summary; before the first save its id follows the name. */
export function changeCity(work: Work, change: Partial<Pick<Definition, 'name' | 'summary' | 'region' | 'country'>>): Definition {
  const next = { ...work.definition, ...change }
  if (change.name !== undefined && !work.saved) next.id = slugify(change.name) || work.definition.id
  return next
}

export function uniqueId(name: string, taken: Iterable<string>): string {
  const used = new Set(taken)
  const base = slugify(name) || 'new'
  let id = base
  for (let count = 2; used.has(id); count++) id = `${base}-${count}`
  return id
}

/** A change made on the table: the summary follows it unless the user wrote their own. */
export function settle(work: Work, definition: Definition, removed?: string): Work {
  const gone = removed ? [...(work.gone ?? []), removed] : work.gone
  const summary = work.brief && !work.summaryEdited ? summaryFor(definition, work.brief) : definition.summary
  return { ...work, definition: { ...definition, summary }, edited: true, gone }
}

const BIOME_WORDS: Record<string, string> = { temperate: '', cold: 'cold, northern ', desert: 'dry, sun-baked ', tropical: 'tropical ', warm: 'sunny southern ', highland: 'mountain ' }
const SIZE_WORDS: Record<string, string> = { tiny: 'village', small: 'small town', town: 'town', large: 'city', huge: 'great city' }

/** "Ridgemouth is a cold, northern town on the sea, with Main Street at its heart and …", as the engine writes it
 * (companion/world/draft summary). */
export function summaryFor(definition: Definition, brief: Brief): string {
  const kind = definition.country.toLowerCase()
  const start = brief.aboard ? `${definition.name} is ${/^[aeiou]/.test(kind) ? 'an' : 'a'} ${kind} of ${definition.neighborhoods.length} decks`
    : `${definition.name} is a ${BIOME_WORDS[brief.biome] ?? ''}${SIZE_WORDS[brief.size] ?? 'town'}${brief.water ? ` ${WATERS[brief.water] ?? ''}` : ''}`
  const names = definition.neighborhoods.slice(0, 4).map((hood) => running(hood.name))
  if (names.length < 2) return names.length ? `${start}, with ${names[0]} at its heart.` : `${start}.`
  const others = names.length > 2 ? `${names.slice(1, -1).join(', ')} and ${names[names.length - 1]}` : names[1]
  return `${start}, with ${names[0]} at its heart and ${others} round about.`
}

/** A name as it reads mid-sentence: "the Waterfront", not "The Waterfront". */
function running(name: string): string {
  return name.startsWith('The ') ? `the${name.slice(3)}` : name
}

/** Parts the user removed that the summary they wrote still names. */
export function staleNames(work: Work): string[] {
  const text = work.definition.summary.toLowerCase()
  return [...new Set(work.gone ?? [])].filter((name) => name && text.includes(running(name).toLowerCase().replace(/^the /, '')))
}

/** A new place in a neighbourhood, like the others there (or the first in the city) until the user changes it. */
export function addPlace(definition: Definition, hood: string): { definition: Definition; id: string } {
  const like = definition.places.find((item) => item.neighborhood === hood) ?? definition.places[0]
  const name = 'New place'
  const id = uniqueId(name, definition.places.map((item) => item.id))
  const hoodName = definition.neighborhoods.find((item) => item.id === hood)?.name ?? definition.name
  const place: Item = { ...(like ? structuredClone(like) : { kind: 'cafe', cost: '$', setting: 'indoor', good_for: ['solo'], day_parts: ['afternoon'] }), id, name, neighborhood: hood, summary: `A new place in ${hoodName}.`, tags: [] }
  return { definition: { ...definition, places: [...definition.places, place] }, id }
}

/** A new neighbourhood beside the others, with the rents and housing of the one it copies. */
export function addHood(definition: Definition): { definition: Definition; id: string } {
  const like = definition.neighborhoods[definition.neighborhoods.length - 1]
  const name = definition.enclosed ? 'New deck' : 'New neighborhood'
  const id = uniqueId(name, definition.neighborhoods.map((item) => item.id))
  const angle = unit(`${definition.id}|${id}`) * 2 * Math.PI
  const hood: Hood = { ...structuredClone(like), id, name, summary: `A new part of ${definition.name}.`, lat: round(definition.lat + 0.012 * Math.sin(angle)), lon: round(definition.lon + 0.012 * Math.cos(angle)) }
  const added = addPlace({ ...definition, neighborhoods: [...definition.neighborhoods, hood] }, id)
  return { definition: added.definition, id }
}

const round = (value: number) => Math.round(value * 1e6) / 1e6

export function hoodNames(definition: Definition): Record<string, string> {
  return Object.fromEntries(definition.neighborhoods.map((hood) => [hood.id, hood.name]))
}

/** The draft drawn the way Companion draws its own map (companion/life/citymap.py), with nothing pinned yet. */
export function mapData(definition: Definition): CityMapData {
  const hoods = new Map(definition.neighborhoods.map((hood) => [hood.id, hood]))
  const places: MapPlace[] = definition.places.flatMap((item) => {
    const hood = hoods.get(item.neighborhood ?? '')
    if (!hood) return []
    const angle = unit(`${item.id}|angle`) * 2 * Math.PI, reach = 0.004 * (0.25 + 0.75 * Math.sqrt(unit(`${item.id}|reach`)))
    return [{ id: item.id, name: item.name, kind: item.kind ?? 'place', hood: hood.name, hood_id: hood.id, lat: hood.lat + reach * Math.sin(angle), lon: hood.lon + reach * Math.cos(angle), approx: true, pins: [], spots: [], history: [], regulars: [] }]
  })
  const near = (hood: Hood) => definition.neighborhoods.filter((other) => other.id !== hood.id)
    .sort((a, b) => Math.hypot(a.lat - hood.lat, a.lon - hood.lon) - Math.hypot(b.lat - hood.lat, b.lon - hood.lon)).slice(0, 2).map((other) => other.id)
  return {
    city: { id: definition.id, name: definition.name, lat: definition.lat, lon: definition.lon, real: false, enclosed: definition.enclosed === true },
    hoods: definition.neighborhoods.map((hood) => ({ id: hood.id, name: hood.name, lat: hood.lat, lon: hood.lon, next: near(hood) })),
    places, water: definition.water ?? [], story: false,
  }
}

/** "1920s, a town on the sea, cold" from the brief, for the facts under the name. */
export function briefLine(brief: Brief | null, definition: Definition): string {
  if (!brief) return [ERAS[definition.era] ?? definition.era, `${definition.neighborhoods.length} ${definition.enclosed ? 'decks' : 'neighborhoods'}`].join(' · ')
  const era = ERAS[brief.era] ?? brief.era
  const size = brief.aboard ? `${definition.country.toLowerCase()} of ${definition.neighborhoods.length} decks` : `${SIZES[brief.size] ?? 'town'}${brief.water ? ` ${WATERS[brief.water] ?? ''}` : ''}`
  return [era, size, brief.aboard ? '' : CLIMATES[brief.biome]].filter(Boolean).join(' · ')
}

const ERAS: Record<string, string> = { medieval: 'Medieval', fantasy: 'Fantasy', victorian: 'Victorian', steampunk: 'Steampunk', frontier: 'Frontier', 'jazz-age': '1920s', modern: 'Today', future: 'The future' }
const SIZES: Record<string, string> = { tiny: 'Village', small: 'Small town', town: 'Town', large: 'City', huge: 'Great city' }
const WATERS: Record<string, string> = { sea: 'on the sea', river: 'on a river', lake: 'by a lake' }
const CLIMATES: Record<string, string> = { temperate: 'Mild', cold: 'Cold', desert: 'Dry', tropical: 'Tropical', warm: 'Warm', highland: 'Mountains' }

/** Lines to start from, for the empty table. */
export const EXAMPLES = ['a cold fishing town on a northern coast, 1920s', 'an elven forest city', 'a generation ship', 'a gaslit victorian port', 'a mining boomtown in the wild west']

/** Place kinds the app knows (companion/world/schema.py PLACE_KINDS), in plain words. */
export const PLACE_KINDS: Record<string, string> = {
  restaurant: 'Restaurant', cafe: 'Café', bar: 'Bar', tavern: 'Tavern', inn: 'Inn', nightlife: 'Nightlife', venue: 'Venue',
  market: 'Market', shopping: 'Shop', park: 'Park', garden: 'Garden', beach: 'Beach', trail: 'Trail', square: 'Square',
  landmark: 'Landmark', attraction: 'Attraction', museum: 'Museum', library: 'Library', stadium: 'Stadium',
  fitness: 'Fitness', temple: 'Temple', guildhall: 'Guildhall', workshop: 'Workshop', docks: 'Docks', vet: 'Vet',
}
export const COLOUR_KINDS: Record<string, string> = { dish: 'Dish', drink: 'Drink', saying: 'Saying', custom: 'Custom', team: 'Team', shop: 'Shop', legend: 'Legend', rumor: 'Rumor', other: 'Other' }
/** Short month names in the user's own language, January first. */
export const MONTHS = Array.from({ length: 12 }, (_, index) => new Date(Date.UTC(2026, index, 15)).toLocaleDateString(undefined, { month: 'short', timeZone: 'UTC' }))

const KEY = 'draft-table-work'
/** Saving a place tells Companion's window, which lists the user's cities, to look again. */
export const CITIES_CHANNEL = 'companion-cities'

export function loadWork(): Work | null {
  try {
    const work = JSON.parse(localStorage.getItem(KEY) ?? 'null') as Work | null
    return work && typeof work.line === 'string' && Array.isArray(work.definition?.neighborhoods) ? work : null
  } catch { return null }
}

export function keepWork(work: Work | null) {
  try { if (work) localStorage.setItem(KEY, JSON.stringify(work)); else localStorage.removeItem(KEY) } catch { /* kept for this visit only */ }
}
