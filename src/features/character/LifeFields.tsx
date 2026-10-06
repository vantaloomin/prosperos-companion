import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition, CitySummary } from '../../types'
import { Field, TextInput } from '../../components/Fields'
import { MoneyFields } from './MoneyFields'
import { ScheduleEditor } from './ScheduleEditor'
import type { DraftField } from './drafting'

interface Props { definition: CharacterDefinition; set: (change: Partial<CharacterDefinition>) => void; themes: string; setThemes: (value: string) => void; help?: (field: DraftField, label: string) => ReactNode }

export function LifeFields({ definition, set, themes, setThemes, help }: Props) {
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
      {help?.('schedule', 'their week')}
      <TextInput label="What their life tends to involve" value={themes} onChange={setThemes} hint="Themes for everyday events, separated by commas, such as cycling, the harbour, their sister." />
      {help?.('life_themes', 'these themes')}
      <TextInput label="Birthday" value={definition.birthday ?? ''} maxLength={5} placeholder="MM-DD" onChange={(value) => set({ birthday: value.trim() })}
        hint="Month and day, such as 07-21. Leave it empty and a date is picked for them. On the day they celebrate, and can tell you." />
      <MoneyFields money={definition.money} homeCity={definition.home_city} onChange={(money) => set({ money })} />
    </>
  )
}
