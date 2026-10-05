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
  distribution: 'public' | 'private'
}

export interface PackReport { folders: string[]; loaded: { id: string; file: string }[]; errors: { file: string; error: string }[] }

/** Keys the server adds when it loads a city; they are not part of a definition. */
const DERIVED = ['data_version', 'builtin', 'origin', 'pack_file', 'revision', 'created_at', 'updated_at']

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

export const GROUPS: { origin: CityListing['origin']; title: string; note: string }[] = [
  { origin: 'user', title: 'Your cities', note: 'Saved in this workspace and carried by backups.' },
  { origin: 'pack', title: 'City packs', note: 'Loaded from a folder on this computer. Copy one to change it.' },
  { origin: 'builtin', title: 'Built in', note: 'Ship with the Companion. Copy one to make it yours.' },
]

export function groupCities(cities: CityListing[]): Record<CityListing['origin'], CityListing[]> {
  const groups: Record<CityListing['origin'], CityListing[]> = { user: [], pack: [], builtin: [] }
  for (const city of [...cities].sort((a, b) => a.name.localeCompare(b.name))) groups[city.origin].push(city)
  return groups
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
