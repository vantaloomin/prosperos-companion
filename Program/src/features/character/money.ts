import { appDate } from '../../appTime.ts'
import type { CareerSummary } from '../../types'

/** The careers of their era; adult work only while the adult side of life is on. Their current one always stays. */
export function careersFor(careers: CareerSummary[], era: string | undefined, current: string, adult = false): CareerSummary[] {
  const fitting = careers.filter((career) => career.id === current || ((!era || career.eras.includes(era)) && (adult || !career.adult)))
  return [...fitting].sort((a, b) => a.name.localeCompare(b.name))
}

/** The Work picker's choices: the careers their home city offers (its era's shared ones and its own, which are the
 * only ones a medieval, fantasy or steampunk city has), else the shared catalogue for their era until the city answers.
 * Their current career always stays, even when the city no longer offers it. */
export function workChoices(offered: CareerSummary[] | undefined, shared: CareerSummary[], era: string | undefined, current: string, adult = false): CareerSummary[] {
  if (!offered) return careersFor(shared, era, current, adult)
  const kept = offered.some((career) => career.id === current) ? [] : shared.filter((career) => career.id === current)
  return careersFor([...offered, ...kept], undefined, current, adult)
}

/** The "Guess from who they are" choice, naming the career it found ("Guess from who they are: Pit fighter"). */
export function guessLabel(guess: CareerSummary | null | undefined): string {
  if (guess === undefined) return 'Guess from who they are'
  return guess ? `Guess from who they are: ${guess.name}` : 'Guess from who they are: an everyday wage for now'
}

export function todayIso(now = appDate()): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
