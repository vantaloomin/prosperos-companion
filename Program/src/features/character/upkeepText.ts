import type { UpkeepArea, UpkeepHabit, UpkeepView } from '../../types'
import { calendarDay } from '../../when.ts'

export const AREA_LABELS: Record<UpkeepArea, string> = { laundry: 'Laundry', dishes: 'Dishes', clutter: 'Clutter' }

export const HABIT_CHOICES: Record<UpkeepHabit, string> = { neat: 'Neat', average: 'Average', messy: 'Messy' }

/** "The laundry is piling up. The dishes are done. The place is tidy.", or where they are while away. */
export function upkeepSummary(view: Pick<UpkeepView, 'away' | 'areas'>): string {
  if (view.away) return 'They are away, so the housework waits for them.'
  return view.areas.map((area) => area.text).join(' ')
}

/** "Mess: Laundry 95 · Dishes 95 · Clutter 95 of 100" for Hidden values: higher is messier. */
export function numbersText(areas: UpkeepView['areas']): string {
  return `Mess: ${areas.map((area) => `${AREA_LABELS[area.area]} ${area.value}`).join(' · ')} of 100`
}

/** When the last big clean was, as a phrase ("yesterday", "last Friday", "Oct 2") and as a month-first date for a
 * hover title, or null when there was none in the last two weeks. */
export function lastClean(view: Pick<UpkeepView, 'last_big_clean' | 'today'>): { when: string; date: string } | null {
  if (!view.last_big_clean) return null
  const date = calendarDay(view.last_big_clean, { weekday: true })
  const days = Math.round((Date.parse(view.today) - Date.parse(view.last_big_clean)) / 86_400_000)
  const weekday = new Date(`${view.last_big_clean}T12:00:00Z`).toLocaleDateString(undefined, { weekday: 'long', timeZone: 'UTC' })
  const when = days <= 0 ? 'today' : days === 1 ? 'yesterday' : days < 7 ? weekday : days < 14 ? `last ${weekday}` : calendarDay(view.last_big_clean)
  return { when, date }
}
