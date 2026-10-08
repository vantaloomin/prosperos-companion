/** The quick start's "Where and when" pick: the catalogue's cities grouped by era, today's first. */
import type { CitySummary } from '../../types'

const ERAS: [string, string][] = [
  ['modern', 'Today'], ['future', 'The future'], ['victorian', 'Victorian'], ['steampunk', 'Steampunk'],
  ['frontier', 'The frontier'], ['medieval', 'Medieval'], ['fantasy', 'Fantasy'],
]

export interface PlaceGroup { label: string; cities: CitySummary[] }

export function placeGroups(cities: CitySummary[]): PlaceGroup[] {
  const known = new Set(ERAS.map(([era]) => era))
  const groups = ERAS.map(([era, label]) => ({ label, cities: cities.filter((city) => (city.era ?? 'modern') === era) }))
  groups.push({ label: 'Other', cities: cities.filter((city) => !known.has(city.era ?? 'modern')) })
  return groups.filter((group) => group.cities.length > 0)
}

/** The city a new companion lives in unless the user picks another: a city of today in the user's own time zone,
 * else one on the same continent, else Baltimore, the first shipped city. "Anywhere, today" stays a pick. */
export function defaultCity(cities: CitySummary[], timezone: string): string {
  const today = cities.filter((city) => (city.era ?? 'modern') === 'modern')
  const continent = timezone.split('/')[0]
  const pick = today.find((city) => city.timezone === timezone) ?? today.find((city) => city.timezone.split('/')[0] === continent)
    ?? today.find((city) => city.id === 'baltimore') ?? today[0]
  return pick?.id ?? ''
}
