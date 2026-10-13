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

/** "Oct 6" for an event's day. */
export function eventDay(event: WorkEvent): string {
  return calendarDay(event.local_date)
}
