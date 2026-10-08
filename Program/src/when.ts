/**
 * How long ago something happened, for message and post timestamps: "just now" and "5 minutes ago" while
 * it is recent, then the clock time, "Yesterday 9:14 PM", the weekday or the date. `now` is the app's time
 * (appTime.ts), so with debug time on a message from before the jump reads as long ago. Times show in the
 * PC's own timezone.
 */
const CLOCK = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })
const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: 'short' })
const DAY = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
const DAY_YEAR = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
const EXACT = new Intl.DateTimeFormat(undefined, { dateStyle: 'full', timeStyle: 'short' })

const MINUTE = 60_000
const HOUR = 60 * MINUTE

function startOfDay(ms: number) {
  const date = new Date(ms)
  date.setHours(0, 0, 0, 0)
  return date.getTime()
}

/** Whole calendar days between the two, by the local calendar (so 11 PM to 1 AM is one day). */
function daysBetween(then: number, now: number) {
  return Math.round((startOfDay(now) - startOfDay(then)) / (24 * HOUR))
}

export function relativeTime(value: string, now: number): string {
  const then = Date.parse(value)
  if (Number.isNaN(then)) return ''
  return recent(now - then, daysBetween(then, now)) ?? calendar(then, now)
}

/** "just now", "5 minutes ago" or "2 hours ago" earlier today; null for anything older or ahead. */
function recent(ago: number, days: number): string | null {
  // A little ahead of the clock (a clock a moment out) still reads as now.
  if (Math.abs(ago) < MINUTE) return 'just now'
  if (ago < 0) return null
  if (ago < HOUR) return count(Math.floor(ago / MINUTE), 'minute')
  if (ago < 3 * HOUR && days === 0) return count(Math.floor(ago / HOUR), 'hour')
  return null
}

function count(amount: number, unit: string) {
  return `${amount} ${unit}${amount === 1 ? '' : 's'} ago`
}

/** The clock time today, "Yesterday 9:14 PM", the weekday within the week, else the date. */
function calendar(then: number, now: number): string {
  const clock = CLOCK.format(then)
  const days = daysBetween(then, now)
  if (days === 0) return clock
  if (days === 1) return `Yesterday ${clock}`
  if (days > 1 && days < 7) return `${WEEKDAY.format(then)} ${clock}`
  const sameYear = new Date(then).getFullYear() === new Date(now).getFullYear()
  return `${(sameYear ? DAY : DAY_YEAR).format(then)}, ${clock}`
}

/** Retro IM's "[9:14 PM]": the clock time alone today, with the date before it on older messages. */
export function clockTime(value: string, now: number): string {
  const then = Date.parse(value)
  if (Number.isNaN(then)) return ''
  const clock = CLOCK.format(then)
  if (daysBetween(then, now) === 0) return clock
  const sameYear = new Date(then).getFullYear() === new Date(now).getFullYear()
  return `${(sameYear ? DAY : DAY_YEAR).format(then)}, ${clock}`
}

/** The full date and time, shown on hover and focus. */
export function exactTime(value: string): string {
  const then = Date.parse(value)
  return Number.isNaN(then) ? '' : EXACT.format(then)
}
