import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CitySummary } from '../../types'
import { Field } from '../../components/Fields'
import { CityOptions } from '../world/CityOptions'
import type { FeaturedCities } from '../world/cityText'
import { CitiesUnavailable } from '../world/CitiesUnavailable'

interface CityPickProps { value: string; onChange: (cityId: string) => void; currentId: string; disabled?: boolean; autoFocus?: boolean }

/** The picker's first option: the app picks a featured city other than this one (companion/worlds.py SOMEWHERE_NEW). */
export const SOMEWHERE_NEW = 'somewhere-new'

/** Where a new world is: somewhere new the app picks unless the user picks a city (Featured first, then every shelf,
 * the current city among them). */
export function CityPick({ value, onChange, currentId, disabled, autoFocus }: CityPickProps) {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const featured = useQuery({ queryKey: ['featured-cities'], queryFn: () => api<FeaturedCities<CitySummary>>('/world/featured'), staleTime: Infinity })
  // The current city is always there to pick, even before the list arrives or when it can't be read.
  const listed = cities.data?.some((city) => city.id === currentId) ? cities.data : [...(cities.data ?? []), { id: currentId, name: 'The city you are in now' }]
  return (<>
    <Field label="Where they live" hint="A new town with new people in it. Days there follow its places and its era.">
      {(id, hint) => (
        <select id={id} aria-describedby={hint} value={value} disabled={disabled} autoFocus={autoFocus} onChange={(event) => onChange(event.target.value)}>
          <option value={SOMEWHERE_NEW}>Somewhere new (picked for you)</option>
          <CityOptions cities={listed} featured={featured.data?.cities} withRegion />
        </select>
      )}
    </Field>
    <CitiesUnavailable cities={cities} />
  </>)
}
