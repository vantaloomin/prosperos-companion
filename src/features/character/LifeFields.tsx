import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition, CitySummary } from '../../types'
import { Field, TextInput } from '../../components/Fields'
import { ScheduleEditor } from './ScheduleEditor'

interface Props { definition: CharacterDefinition; set: (change: Partial<CharacterDefinition>) => void; themes: string; setThemes: (value: string) => void }

export function LifeFields({ definition, set, themes, setThemes }: Props) {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const chooseCity = (id: string) => {
    const city = cities.data?.find((item) => item.id === id)
    // A home city sets their clock too; it can still be changed above.
    set(city ? { home_city: id, timezone: city.timezone, location: definition.location || `${city.name}, ${city.region}` } : { home_city: '' })
  }
  return (
    <>
      <Field label="Home city" hint="With a home city, their days use real neighbourhoods and places there. Without one, their life stays general.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={definition.home_city} onChange={(event) => chooseCity(event.target.value)}>
            <option value="">None</option>
            {(cities.data ?? []).map((city) => <option key={city.id} value={city.id}>{city.name}, {city.region}</option>)}
          </select>
        )}
      </Field>
      <ScheduleEditor blocks={definition.schedule} onChange={(schedule) => set({ schedule })} timezone={definition.timezone} />
      <TextInput label="What their life tends to involve" value={themes} onChange={setThemes} hint="Themes for everyday events, separated by commas, such as cycling, the harbour, their sister." />
    </>
  )
}
