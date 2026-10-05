import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CareerSummary, CitySummary, MoneySetup, SpendingStyle } from '../../types'
import { Field, TextInput } from '../../components/Fields'
import { careersFor, todayIso } from './money'

const STYLES: { value: SpendingStyle; label: string }[] = [
  { value: 'careful', label: 'Careful: saves first, rarely runs short' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'spender', label: 'Spender: treats themselves, often broke before payday' },
]

interface Props { money: MoneySetup; homeCity: string; onChange: (money: MoneySetup) => void }

/** Their work and money habits; pay, rent and prices come from their home city's data. */
export function MoneyFields({ money, homeCity, onChange }: Props) {
  const careers = useQuery({ queryKey: ['careers'], queryFn: () => api<CareerSummary[]>('/world/careers'), staleTime: Infinity })
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const era = cities.data?.find((city) => city.id === homeCity)?.era
  const set = (change: Partial<MoneySetup>) => onChange({ ...money, ...change })
  // A new goal starts counting savings from today.
  const setGoal = (change: Partial<MoneySetup>) => set({ ...change, goal_since: todayIso() })
  return (
    <fieldset className="traits">
      <legend>Work and money</legend>
      <p className="subtle">Their pay comes from their work and their rent from their home city, so some weeks are tight and some are flush. You can see their budget on Today.</p>
      <Field label="Work" hint="Sets their pay. Left on the guess, it comes from what “Who they are” says.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.career} onChange={(event) => set({ career: event.target.value })}>
            <option value="">Guess from who they are</option>
            {careersFor(careers.data ?? [], era, money.career).map((career) => <option key={career.id} value={career.id}>{career.name} ({career.pay})</option>)}
          </select>
        )}
      </Field>
      <Field label="Spending style">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.style} onChange={(event) => set({ style: event.target.value as SpendingStyle })}>
            {STYLES.map((style) => <option key={style.value} value={style.value}>{style.label}</option>)}
          </select>
        )}
      </Field>
      <TextInput label="Saving for" value={money.saving_for} onChange={(saving_for) => setGoal({ saving_for })} maxLength={120} hint="Optional, such as a trip to Lisbon. Left empty, they pick everyday goals of their own." />
      {money.saving_for && <TextInput label="Goal amount" type="number" value={money.goal ? String(money.goal) : ''} onChange={(value) => setGoal({ goal: Math.max(Number(value) || 0, 0) })} hint="In their city's currency. Left empty, it is sized to what they can save in about six months." />}
    </fieldset>
  )
}
