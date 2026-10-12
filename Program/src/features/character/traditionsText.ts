import { calendarDay } from '../../when.ts'

/** "Next: Thu, Nov 26" for a local date ("2026-11-26"), in the user's own locale (when.ts's calendarDay). */
export function nextText(day: string | null): string | null {
  return day ? `Next: ${calendarDay(day, { weekday: true })}` : null
}

/** "Up at home right now: a wreath on the front door and a carved pumpkin on the front step." */
export function decorationsText(items: string[]): string {
  const list = items.length > 1 ? `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}` : items[0]
  return `Up at home right now: ${list}.`
}
