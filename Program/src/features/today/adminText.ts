/** Life admin (companion/life/admin.py): wording for appointments, errands and chores on Today and the Character page. */
import type { AdminItem } from '../../types'
import { dayText, timeText } from './outingText'

export const ADMIN_KEY = ['life-admin']

/** "Tue, Oct 6, 5:30 PM at Enoch Pratt Free Library". */
export function adminWhen(item: AdminItem): string {
  // A late night at work shows how long it runs: "3:30 PM" alone reads as an afternoon (Iris).
  if (item.source === 'work' && item.at_time && item.until) return `${dayText(item.local_date)}, ${timeText(item.at_time)} to ${timeText(item.until)}`
  // A stay with the other parent runs from its first day to its last (companion/life/stays.py).
  if (item.end_date && item.end_date !== item.local_date) return `${dayText(item.local_date)} to ${dayText(item.end_date)}`
  const at = item.at_time ? `${dayText(item.local_date)}, ${timeText(item.at_time)}` : dayText(item.local_date)
  return item.place ? `${at} at ${item.place}` : at
}

/** "Put off from Tue, Oct 6", "Moved for a plan from Tue, Oct 6", or nothing. */
export function adminMoved(item: AdminItem): string {
  if (!item.moved_reason || !item.moved_from || item.moved_from === item.local_date) return ''
  const reason = item.moved_reason.charAt(0).toUpperCase() + item.moved_reason.slice(1)
  return `${reason} from ${dayText(item.moved_from)}`
}

/** Booked with someone else, or something they can do any time; and its cost when it has one. */
export function adminTags(item: AdminItem, inWorkPanel = false): string[] {
  // Work life's late nights, in Life admin's words for who gives way (Iris): the panel already says it is work.
  if (item.source === 'work' && inWorkPanel) return item.fixed ? ["Won't give way"] : []
  if (item.source === 'work') return [item.fixed ? "Work · won't give way" : 'Work']
  if (item.source === 'family') return item.status === 'skipped' ? ['Skipped'] : []
  return [item.fixed ? 'Booked' : '', item.cost_text].filter(Boolean)
}

/** What a stay moves by: 'weekend', 'week' or 'day' (companion/life/stays.py moves it a week on). */
export function stayUnit(item: AdminItem): string {
  if (!item.end_date || item.end_date === item.local_date) return 'day'
  const days = (Date.parse(item.end_date) - Date.parse(item.local_date)) / 86_400_000 + 1
  return days >= 6 ? 'week' : 'weekend'
}
