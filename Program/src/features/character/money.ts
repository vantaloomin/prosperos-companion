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

/** The "Guess from who they are" choice, naming the career it found ("Guess from who they are: Pit fighter ($$)"). */
export function guessLabel(guess: CareerSummary | null | undefined): string {
  if (guess === undefined) return 'Guess from who they are'
  return guess ? `Guess from who they are: ${guess.name} (${guess.pay})` : 'Guess from who they are: no job named'
}

/** The Work picker's "Something else": work the user writes in (companion/life/money.py OWN). */
export const OWN_WORK = 'own'

/** The Work hint: on a guess that found no job, why they earn an everyday wage; for work of their own, what sets its
 * hours. With a pay of their own set, it says nothing about pay (Iris). */
export function workHint(guess: CareerSummary | null | undefined, own = false, paySet = false): string {
  if (own) return 'Hours follow a job it names, such as nurse; otherwise office hours.'
  if (guess === null) {
    return paySet ? 'Nothing in “Who they are” names a job. Pick one to set it.'
      : 'Nothing in “Who they are” names a job, so they earn an everyday wage. Pick one to set it.'
  }
  return paySet ? 'Sets their hours and kind of work. Their pay is set below.'
    : 'Sets their pay. Left on the guess, it comes from what “Who they are” says.'
}

/** A whole number with thousands separators (3,100), or '' for a pay left to their work. */
export function payText(pay: number | null | undefined): string {
  return pay === null || pay === undefined ? '' : Math.round(pay).toLocaleString('en-US')
}

/** Only the digits and separators someone types into Pay. */
export function payDraft(text: string): string {
  return text.replace(/[^\d,]/g, '').slice(0, 13)
}

/** The pay a typed box means: null when empty (worked out), else the whole number (0 is unpaid). */
export function readPay(text: string): number | null {
  const digits = text.replace(/\D/g, '')
  return digits ? Math.min(Number(digits), 1_000_000_000) : null
}

/** The empty Pay box's words: what their work pays ("About 2,400 a month from their work"). */
export function payPlaceholder(monthly: number | undefined): string {
  return monthly === undefined ? 'Worked out from their work and city' : `About ${payText(monthly)} a month from their work`
}

export function todayIso(now = appDate()): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
