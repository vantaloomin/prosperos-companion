/** Pure helpers for the city builder, kept apart from the components so they can be tested directly. */

export interface CityListing {
  id: string
  name: string
  region: string
  country: string
  setting: 'real' | 'fictional' | 'original'
  era: string
  summary: string
  basis: string
  counts: Record<'neighborhoods' | 'places' | 'colleges' | 'employers' | 'annual_events', number>
  builtin: boolean
  origin: 'builtin' | 'pack' | 'user'
  /** The city's shelf in city lists, decided by the server (companion/world/catalog.py `category`). */
  category?: string
  aliases?: string[]
  distribution: 'public' | 'private'
  /** What the server mended or added when it loaded the city; empty when it loaded as written. */
  import_notes?: string[]
}

/** One of the user's own cities that no longer loads, with its saved definition. */
export interface BrokenCity { id: string; name: string; error: string; definition: unknown }

export interface PackReport { folders: string[]; loaded: { id: string; file: string; import_notes?: string[] }[]; errors: { file: string; error: string }[] }

/** Keys the server adds when it loads a city; they are not part of a definition. */
const DERIVED = ['data_version', 'builtin', 'origin', 'pack_file', 'revision', 'created_at', 'updated_at', 'import_notes']

export function definitionOf(city: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(city).filter(([key]) => !DERIVED.includes(key)))
}

export function slugify(text: string): string {
  return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80)
}

export type Parsed = { ok: true; value: Record<string, unknown> } | { ok: false; error: string }

/** Parse the editor's text as a city definition, with a readable message when it is not one. */
export function parseDefinition(text: string): Parsed {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch (error) {
    return { ok: false, error: `This is not valid JSON: ${error instanceof Error ? error.message : 'it could not be read'}.` }
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return { ok: false, error: 'A city is a JSON object, starting with {.' }
  return { ok: true, value: value as Record<string, unknown> }
}

export type CityCategory = 'real' | 'other-eras' | 'fictional' | 'custom'

export const CATEGORIES: { id: CityCategory; title: string }[] = [
  { id: 'real', title: 'Real / Modern' }, { id: 'other-eras', title: 'Other Eras' },
  { id: 'fictional', title: 'Fictional' }, { id: 'custom', title: 'Custom' },
]

interface Shelved { name: string; category?: string }

/** The city's shelf; a city the server sent without one (an older server, or a scene's own city) counts as real. */
export function categoryOf(city: Shelved): CityCategory {
  return CATEGORIES.some((item) => item.id === city.category) ? city.category as CityCategory : 'real'
}

export interface Shelf<T> { id: CityCategory; title: string; cities: T[] }

/** Every shelf in order, each sorted by name. Empty shelves are kept so a list can say "None yet". */
export function shelveCities<T extends Shelved>(cities: T[]): Shelf<T>[] {
  const sorted = [...cities].sort((a, b) => a.name.localeCompare(b.name))
  return CATEGORIES.map((item) => ({ ...item, cities: sorted.filter((city) => categoryOf(city) === item.id) }))
}

const fold = (text: string) => text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()

/** Whether a city matches what was typed into the city search: its name, other names, region or country. */
export function matchesCity(city: Pick<CityListing, 'name' | 'region' | 'country' | 'aliases'>, query: string): boolean {
  const wanted = fold(query.trim())
  return !wanted || [city.name, city.region, city.country, ...(city.aliases ?? [])].some((text) => fold(text).includes(wanted))
}

const SETTINGS: Record<CityListing['setting'], string> = { real: 'Real city', fictional: 'Fictional setting', original: 'Original setting' }

/** "Real city · modern · 21 neighbourhoods, 124 places" */
export function cityFacts(city: CityListing): string {
  const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`
  return [SETTINGS[city.setting], city.era,
    `${plural(city.counts.neighborhoods, 'neighbourhood', 'neighbourhoods')}, ${plural(city.counts.places, 'place', 'places')}`].join(' · ')
}

/** A file name for an exported city. */
export function exportName(id: string): string {
  return `${slugify(id) || 'city'}.json`
}
