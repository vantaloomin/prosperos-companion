/** Engagement and wedding (companion/life/wedding.py): the Life admin panel's wording, kept apart for tests. */
import type { WeddingPlan } from '../../types.ts'
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

/** Tomorrow as a local ISO date: the earliest day the wedding can move to. */
export function tomorrow(today = new Date()): string {
  const next = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`
}
