import type { StoryVisit } from '../../types'

/** "2:06" and "PM" from a local time ("2026-11-16T14:06"), which is the companion's own clock with no offset. */
function clock(localTime: string): [string, string] {
  const [hour, minute] = localTime.slice(11, 16).split(':').map(Number)
  return [`${hour % 12 || 12}:${String(minute).padStart(2, '0')}`, hour < 12 ? 'AM' : 'PM']
}

/** A finished Story visit as their chat says it (companion/story_visits.py): "In Story at Club Charles · 2:06 to
 * 2:31 PM", "11:50 AM to 12:20 PM" across noon, and one time when it began and ended in the same minute. */
export function visitText(visit: Pick<StoryVisit, 'place' | 'from' | 'until'>): string {
  const [from, fromHalf] = clock(visit.from), [until, untilHalf] = clock(visit.until)
  const when = visit.from === visit.until ? `${until}\u00a0${untilHalf}`
    : `${from}${fromHalf === untilHalf ? '' : `\u00a0${fromHalf}`} to ${until}\u00a0${untilHalf}`
  return `In Story at ${visit.place} · ${when}`
}
