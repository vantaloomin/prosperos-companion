/** Life admin (companion/life/admin.py): wording for appointments, errands and chores on Today and the Character page. */
import type { AdminItem } from '../../types'
import { dayText, timeText } from './outingText'

export const ADMIN_KEY = ['life-admin']

/** "Tue, Oct 6, 5:30 PM at Enoch Pratt Free Library". */
export function adminWhen(item: AdminItem): string {
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
export function adminTags(item: AdminItem): string[] {
  if (item.source === 'work') return [item.fixed ? 'Work, keeps its time' : 'Work']
  return [item.fixed ? 'Booked' : '', item.cost_text].filter(Boolean)
}
