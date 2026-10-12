import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CitySummary } from '../../types'
import { Field } from '../../components/Fields'
import { CityOptions } from '../world/CityOptions'
import type { FeaturedCities } from '../world/cityText'
import { CitiesUnavailable } from '../world/CitiesUnavailable'

interface CityPickProps { value: string; onChange: (cityId: string) => void; currentId: string; disabled?: boolean; autoFocus?: boolean }

/** Where a new world is: the city the user is in now unless they pick another (Featured first, then every shelf). */
export function CityPick({ value, onChange, currentId, disabled, autoFocus }: CityPickProps) {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const featured = useQuery({ queryKey: ['featured-cities'], queryFn: () => api<FeaturedCities<CitySummary>>('/world/featured'), staleTime: Infinity })
  // The current city is always there to pick, even before the list arrives or when it can't be read.
  const listed = cities.data?.some((city) => city.id === currentId) ? cities.data : [...(cities.data ?? []), { id: currentId, name: 'The city you are in now' }]
  return (<>
    <Field label="Where they live" hint="A new town with new people in it. Days there follow its places and its era.">
      {(id, hint) => (
        <select id={id} aria-describedby={hint} value={value} disabled={disabled} autoFocus={autoFocus} onChange={(event) => onChange(event.target.value)}>
          <CityOptions cities={listed} featured={featured.data?.cities} withRegion />
        </select>
      )}
    </Field>
    <CitiesUnavailable cities={cities} />
  </>)
}
