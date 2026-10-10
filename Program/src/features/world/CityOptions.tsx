import { shelveCities } from './cityText'

interface Option { id: string; name: string; region?: string; category?: string }

/** A city select's options, grouped Real / Modern, Other Eras, Fictional and Custom, each A to Z. */
export function CityOptions({ cities, withRegion = false }: { cities: Option[]; withRegion?: boolean }) {
  return shelveCities(cities).filter((shelf) => shelf.cities.length > 0).map((shelf) => (
    <optgroup key={shelf.id} label={shelf.title}>
      {shelf.cities.map((city) => <option key={city.id} value={city.id}>{withRegion && city.region ? `${city.name}, ${city.region}` : city.name}</option>)}
    </optgroup>
  ))
}
