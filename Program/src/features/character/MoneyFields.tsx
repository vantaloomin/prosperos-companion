import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CareerSummary, CharacterDefinition, CitySummary, Employment, HomeTenure, MoneySetup, SpendingStyle } from '../../types'
import { Field, TextInput } from '../../components/Fields'
import { useWorkspaceSettings } from '../../companion'
import { guessLabel, OWN_WORK, todayIso, workChoices, workHint } from './money'
import { useSettled } from './useSettled'
import { PayField } from './PayField'

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

/** How they hold their home (companion/life/owning.py); a medieval kingdom pays a place off, with no mortgage. */
function homeChoices(medieval: boolean): { value: HomeTenure; label: string }[] {
  return [
    { value: '', label: 'Picked for them' },
    { value: 'rent', label: 'Renting' },
    { value: 'mortgage', label: medieval ? 'Paying it off' : 'Paying off a mortgage' },
    { value: 'owned', label: 'Owns it outright' },
  ]
}

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

/** Their home city's era, for the words the pickers use. */
function useEra(homeCity: string): string | undefined {
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  return cities.data?.find((city) => city.id === homeCity)?.era
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
  const era = useEra(definition.home_city)
  const guess = useGuess(definition, money.career === '')
  const guessed = definition.home_city ? guess.data : undefined
  // Adult work sits in its own group at the end, so the everyday list stays easy to scan.
  const option = (career: CareerSummary) => <option key={career.id} value={career.id}>{career.name} ({career.pay})</option>
  const set = (change: Partial<MoneySetup>) => onChange({ ...money, ...change })
  const own = money.career === OWN_WORK
  const paySet = money.pay !== null && money.pay !== undefined
  // Picking "Something else" moves to the box to write it in.
  const pick = (career: string) => {
    set({ career })
    if (career === OWN_WORK) requestAnimationFrame(() => document.querySelector<HTMLInputElement>('[data-own-work] input')?.focus())
  }
  // A new goal starts counting savings from today.
  const setGoal = (change: Partial<MoneySetup>) => set({ ...change, goal_since: todayIso() })
  return (
    <fieldset className="traits">
      <legend>Work and money</legend>
      <p className="subtle">Their pay comes from their work and what their home costs from their home city, so some weeks are tight and some are flush. You can see their budget on Today.</p>
      <Field label="Work" hint={workHint(money.career ? undefined : guessed, own, paySet)}>
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.career} onChange={(event) => pick(event.target.value)}>
            <option value="">{guessLabel(guessed)}</option>
            {listed.filter((career) => !career.adult).map(option)}
            <hr />
            <option value={OWN_WORK}>Something else (write it in)</option>
            {listed.some((career) => career.adult) && <optgroup label="Adult work">{listed.filter((career) => career.adult).map(option)}</optgroup>}
          </select>
        )}
      </Field>
      {own && <div data-own-work><TextInput label="What they do" value={money.job ?? ''} maxLength={60} onChange={(job) => set({ job })}
        placeholder="Such as tarot reader at the night market" hint="Left empty, it goes back to the guess." /></div>}
      {studies(money.career, guessed) && <TextInput label="What they study" value={money.field ?? ''} maxLength={60}
        onChange={(field) => set({ field })} hint="For a student, such as Photography. Their coursework follows it. Left empty, it comes from what “Who they are” says." />}
      <PayField definition={definition} onChange={(pay) => set({ pay })} />
      <Field label="Hours" hint="Left as their work goes, a bartender or nurse gets new shifts each week and a freelancer has gigs that come and go; an office job keeps the same days.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.employment} onChange={(event) => set({ employment: event.target.value as Employment })}>
            {HOURS.map((hours) => <option key={hours.value} value={hours.value}>{hours.label}</option>)}
          </select>
        )}
      </Field>
      <Field label="Home" hint="Left as picked for them, their own words, age and pay decide whether they rent or own. Owners pay taxes and repairs on top, and owning outright means no rent at all.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={money.home ?? ''} onChange={(event) => set({ home: event.target.value as HomeTenure })}>
            {homeChoices(era === 'medieval' || era === 'fantasy').map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
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
