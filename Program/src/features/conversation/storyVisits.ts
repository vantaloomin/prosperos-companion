import type { StoryVisit } from '../../types'
import { clockRange } from '../../when.ts'

/** A finished Story visit as their chat says it (companion/story_visits.py): "In Story at Club Charles · 2:06 to
 * 2:31 PM", with the date first once it is not today. The times are on the clock the chat's own stamps are on (the
 * PC's), since the line sits between them (Iris). */
export function visitText(visit: Pick<StoryVisit, 'place' | 'from' | 'until'>, now: number): string {
  return `In Story at ${visit.place} · ${clockRange(visit.from, visit.until, now)}`
}
