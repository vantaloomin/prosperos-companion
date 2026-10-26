import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CareerSummary, CharacterDefinition, CitySummary, Employment, MoneySetup, SpendingStyle } from '../../types'
import { Field, TextInput } from '../../components/Fields'
import { useWorkspaceSettings } from '../../companion'
import { guessLabel, todayIso, workChoices } from './money'
import { useSettled } from './useSettled'

const STYLES: { value: SpendingStyle; label: string }[] = [
  { value: 'careful', label: 'Careful: saves first, rarely runs short' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'spender', label: 'Spender: treats themselves, often broke before payday' },
]

const HOURS: { value: Employment; label: string }[] = [
  { value: '', label: 'As their work goes' },
  { value: 'staff', label: 'Same days every week' },
  { value: 'rota', label: 'Shifts that change each week' },
  { value: 'freelance', label: 'Freelance gigs, busy and quiet spells' },
]

// Careers whose work is coursework (companion/life/work.py STUDY).
const STUDENTS = new Set(['undergraduate', 'graduate-student'])

/** Whether they study: a student career picked, or the guess is one (or has found nothing yet). */
function studies(career: string, guess: CareerSummary | null | undefined): boolean {
  return career ? STUDENTS.has(career) : !guess || STUDENTS.has(guess.id)
}

interface Props { definition: CharacterDefinition; onChange: (money: MoneySetup) => void }

/** What "Guess from who they are" finds in their home city right now (companion/life/money.py `career_for`). */
function useGuess(definition: CharacterDefinition, asking: boolean) {
  const { name, identity, background, routine, appearance, personality, home_city: homeCity } = useSettled(definition)
  const words = { name, identity, background, routine, appearance, personality }
  return useQuery({
    queryKey: ['career-guess', homeCity, words], enabled: asking && homeCity !== '',
    queryFn: () => api<CareerSummary | null>(`/world/cities/${encodeURIComponent(homeCity)}/careers/guess`, words),
    staleTime: Infinity, placeholderData: (previous) => previous,
  })
}

/** The careers the Work picker offers in their home city (see `workChoices`). */
function useWorkChoices({ money, home_city: homeCity }: CharacterDefinition): CareerSummary[] {
  const careers = useQuery({ queryKey: ['careers'], queryFn: () => api<CareerSummary[]>('/world/careers'), staleTime: Infinity })
  const offered = useQuery({
    queryKey: ['careers', homeCity], enabled: homeCity !== '', staleTime: Infinity,
    queryFn: () => api<CareerSummary[]>(`/world/cities/${encodeURIComponent(homeCity)}/careers`),
  })
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  const era = cities.data?.find((city) => city.id === homeCity)?.era
  const adult = useWorkspaceSettings().data?.adult_side === true
  return workChoices(homeCity ? offered.data : undefined, careers.data ?? [], era, money.career, adult)
}

/** Their work and money habits; pay, rent and prices come from their home city's data. */
export function MoneyFields({ definition, onChange }: Props) {
  const { money } = definition
  const listed = useWorkChoices(definition)
  const guess = useGuess(definition, money.career === '')
  // Adult work sits in its own group at the end, so the everyday list stays easy to scan.
  const option = (career: CareerSummary) => <option key={career.id} value={career.id}>{career.name} ({career.pay})</option>
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
            <option value="">{guessLabel(definition.home_city ? guess.data : undefined)}</option>
            {listed.filter((career) => !career.adult).map(option)}
            {listed.some((career) => career.adult) && <optgroup label="Adult work">{listed.filter((career) => career.adult).map(option)}</optgroup>}
          </select>
        )}
      </Field>
      {studies(money.career, definition.home_city ? guess.data : undefined) && <TextInput label="What they study" value={money.field ?? ''} maxLength={60}
        onChange={(field) => set({ field })} hint="For a student, such as Photography. Their coursework follows it. Left empty, it comes from what “Who they are” says." />}
      <Field label="Hours" hint="Left as their work goes, a bartender or nurse gets new shifts each week and a freelancer has gigs that come and go; an office job keeps the same days.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.employment} onChange={(event) => set({ employment: event.target.value as Employment })}>
            {HOURS.map((hours) => <option key={hours.value} value={hours.value}>{hours.label}</option>)}
          </select>
        )}
      </Field>
      <Field label="Spending style" hint="How they handle money between paydays. It shows up in what they can afford and talk about.">
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
