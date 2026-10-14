/** Wording for the Work life panel (companion/life/work.py). */
import type { WorkEvent } from '../../types'
import { calendarDay } from '../../when.ts'

export const WORK_KEY = ['life-work']

/** The Work life slider's steps (companion/life/work.py LEVELS). */
export const WORK_LEVELS = [
  { label: 'Off', hint: 'Their job stays as written: no busy weeks, no projects, no raises or time off.' },
  { label: 'Steady', hint: 'A steady job: mostly ordinary weeks, a raise once a year and vacation days. Late nights are rare and always move for plans with you.' },
  { label: 'True to life', hint: 'Slammed weeks and slow ones, a project with a deadline, a yearly raise that is now and then a promotion or a freeze. A late night in a slammed week keeps its time; you can still move it.' },
  { label: 'Dramatic', hint: 'More slammed weeks and late nights, and now and then a rough project. Rarely they get laid off or quit, and job hunt for a few weeks.' },
]

/** "Got the yearly raise, about 3.2%" with a capital. */
export function eventText(event: WorkEvent): string {
  return event.text.charAt(0).toUpperCase() + event.text.slice(1)
}

/** "Oct 6" with a no-break space, so a date never splits across lines (Iris). */
function day(iso: string, options?: { weekday?: boolean }): string {
  return calendarDay(iso, options).replace(/ (?=\d)/g, '\u00a0')
}

/** "Oct 6" for an event's day. */
export function eventDay(event: WorkEvent): string {
  return day(event.local_date)
}

/** Runs of vacation days a weekend or less apart, as [first, last, count]. */
function runs(days: string[]): [string, string, number][] {
  const result: [string, string, number][] = []
  for (const day of [...days].sort()) {
    const last = result[result.length - 1]
    if (last && (Date.parse(day) - Date.parse(last[1])) / 86400000 <= 3) { last[1] = day; last[2] += 1 } else result.push([day, day, 1])
  }
  return result
}

/** "1 vacation day coming up: Fri, Nov 13.", "Vacation days coming up: Fri, Nov 6 and Fri, Dec 4." or "Vacation Nov 23 to
 * 27 (5 days)." (Iris); "No time off booked." */
export function timeOffText(days: string[]): string {
  if (!days.length) return 'No time off booked.'
  const found = runs(days)
  // Single days read as one list (Iris): "Vacation days coming up: Fri, Nov 6, Fri, Dec 4 and Fri, Dec 11."
  const single = found.filter(([, , count]) => count === 1).map(([first]) => day(first, { weekday: true }))
  const singles = single.length === 1 ? `1 vacation day coming up: ${single[0]}.`
    : single.length ? `Vacation days coming up: ${single.slice(0, -1).join(', ')} and ${single[single.length - 1]}.` : ''
  const stretches = found.filter(([, , count]) => count > 1).map(([first, last, count]) => `Vacation ${day(first)} to ${day(last)} (${count} days).`)
  return [...stretches, singles].filter(Boolean).join(' ')
}

/** "Vacation: 2 of 11 days used this year. Pay: 3% above where they started." */
export function meterText(meter: { vacation_total: number; vacation_used: number; pay_percent: number }): string {
  const change = meter.pay_percent - 100
  const pay = change > 0 ? `${change}% above` : change < 0 ? `${-change}% below` : 'the same as'
  const vacation = meter.vacation_total ? `Vacation: ${meter.vacation_used} of ${meter.vacation_total} days used this year. ` : 'No paid vacation where they live. '
  return `${vacation}Pay: ${pay} where they started.`
}
