/** Engagement and wedding (companion/life/wedding.py): the wedding card's wording, kept apart for tests. */
import type { WeddingPlan } from '../../types.ts'
import { appDate } from '../../appTime.ts'
import { calendarDay } from '../../when.ts'

/** "A proper wedding on Sat, Jun 12, 2027 at The Belvedere, about 80 guests." */
export function planLine(plan: Pick<WeddingPlan, 'size' | 'size_label' | 'date' | 'venue' | 'guest_count'>): string {
  const size = plan.size === 'proper' ? plan.size_label : `A ${plan.size_label.toLowerCase()} wedding`
  return `${size} on ${calendarDay(plan.date, { weekday: true, year: true })} at ${plan.venue.name}, about ${plan.guest_count} guests.`
}

/** "Budget about $24,000; Mira's share, about $12,000, comes from their savings." Empty where money doesn't apply. */
export function budgetLine(plan: Pick<WeddingPlan, 'budget_text' | 'share_text'>, who: string): string {
  if (!plan.budget_text) return ''
  const share = plan.share_text ? `; ${who}'s share, about ${plan.share_text}, comes from their savings` : ''
  return `Budget about ${plan.budget_text}${share}.`
}

/** "About 80 guests, family and friends from both sides." */
export function guestCount(plan: Pick<WeddingPlan, 'guest_count' | 'size'>): string {
  const who = plan.size === 'small' ? 'close family and a few friends' : 'family and friends from both sides'
  return `About ${plan.guest_count} guests, ${who}.`
}

/** "With Ana (Mira's sister), Jo (your friend) and about 90 more" on the scrapbook page. */
export function guestsLine(guests: string[], more: number): string {
  if (!more) return `With ${guests.join(', ')}`
  return `With ${guests.join(', ')} and about ${more} more`
}

/** "Booked the wedding venue, Aug 17." or "Book the wedding venue by Aug 17.": the plan's one task as a line. */
export function taskLine(task: { title: string; date: string; done: boolean; done_text?: string }, day: (date: string) => string): string {
  return task.done ? `${task.done_text || task.title}, ${day(task.date)}.` : `${task.title} by ${day(task.date)}.`
}

// Today's "Change the plan" opens the Character page; the wedding card scrolls itself into view once it is there.
let opening = false
export function openWedding(): void { opening = true }
export function takeOpening(): boolean {
  const found = opening
  opening = false
  return found
}

/** Tomorrow as a local ISO date: the earliest day the wedding can move to. */
export function tomorrow(today = appDate()): string {
  const next = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`
}
