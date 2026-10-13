import type { UpkeepArea, UpkeepHabit, UpkeepView } from '../../types'
import { calendarDay } from '../../when.ts'

export const AREA_LABELS: Record<UpkeepArea, string> = { laundry: 'Laundry', dishes: 'Dishes', clutter: 'Clutter' }

export const HABIT_CHOICES: Record<UpkeepHabit, string> = { neat: 'Neat', average: 'Average', messy: 'Messy' }

/** "The laundry is piling up. The dishes are done. The place is tidy.", or where they are while away. */
export function upkeepSummary(view: Pick<UpkeepView, 'away' | 'areas'>): string {
  if (view.away) return 'They are away, so the housework waits for them.'
  return view.areas.map((area) => area.text).join(' ')
}

/** "Last big clean: Sat, Oct 10.", or nothing when there was none in the last two weeks. */
export function lastCleanText(view: Pick<UpkeepView, 'last_big_clean'>): string {
  return view.last_big_clean ? `Last big clean: ${calendarDay(view.last_big_clean, { weekday: true })}.` : ''
}
