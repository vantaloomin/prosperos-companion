import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import type { CharacterDefinition, CitySummary, Companion, TheirHours as Hours } from '../../types'
import { Toggle } from '../../components/Fields'
import { clockGap, hoursHint } from './theirHoursText'

interface Props { definition: CharacterDefinition; companion: Companion | null; set: (change: Partial<CharacterDefinition>) => void }

const CITY_HOURS: Hours = { mode: 'city', shift: 0, why: '', zone: '', fit: 0 }

/** The user's zone when it is known (from this PC or chosen) and differs from theirs, else null: nothing to show. */
function useYourZone(definition: CharacterDefinition, companion: Companion | null): string | null {
  const settings = useWorkspaceSettings()
  const yours = settings.data?.user_timezone
  if (!companion || !yours || settings.data?.user_timezone_source === 'default') return null
  const differs = clockGap(definition.timezone, yours) !== 0 || definition.their_hours?.mode === 'mine'
  return differs ? yours : null
}

/** Live on my clock (companion/life/their_hours.py): for a companion whose city keeps another time, their whole day on
 * the user's clock, and the app's own fitting of their week to the user's evenings, with a way to put it back. The form
 * only says which; the server moves the week when it is saved. */
export function TheirHoursField({ definition, companion, set }: Props) {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const yours = useYourZone(definition, companion)
  if (!yours || !companion) return null
  const hours = definition.their_hours ?? CITY_HOURS
  const saved = companion.version.definition.their_hours?.mode ?? 'city'
  const city = cities.data?.find((item) => item.id === definition.home_city)?.name ?? ''
  const mode = (next: Hours['mode']) => set({ their_hours: { ...hours, mode: next } })
  const on = hours.mode === 'mine'
  return (
    <div className="their-hours">
      <Toggle label="Live on my clock" checked={on} onChange={(value) => mode(value ? 'mine' : hours.fit ? 'fit' : 'city')}
        hint={hoursHint({ hours, saved, city, gap: clockGap(definition.timezone, yours) })} tip="Only their routine moves. Their city keeps its own time, weather and news.">
        <FitLink hours={hours} mode={mode} />
      </Toggle>
    </div>
  )
}

/** When the app fitted their week to the user's evenings: a way back to their city's hours, and forward again. The
 * change waits for Save, like the rest of the form, and the hint above says what saving does. */
function FitLink({ hours, mode }: { hours: Hours; mode: (next: Hours['mode']) => void }) {
  if (!hours.fit || hours.mode === 'mine') return null
  const back = hours.mode === 'fit'
  return <button type="button" className="text-button their-hours-link" onClick={() => mode(back ? 'city' : 'fit')}>{back ? "Use their city's hours" : 'Fit them to my evenings'}</button>
}
