import { calendarDay } from '../../when.ts'
import type { ScrapbookListing, ScrapbookPage } from '../../types'

export const SCRAPBOOKS_KEY = ['scrapbooks']

/** "Mar 10, 2025 to Mar 9, 2026" for a scrapbook's dates, without shifting them through a timezone: the year once
 * when both ends share it ("Mar 10 to Sep 6, 2026"), and one date when they are the same day (Iris). */
export function spanText(start: string, end: string): string {
  if (start.slice(0, 10) === end.slice(0, 10)) return dayText(end, true)
  const sameYear = start.slice(0, 4) === end.slice(0, 4)
  return `${dayText(start, !sameYear)} to ${dayText(end, true)}`
}

/** "Mar 10" or "Mar 10, 2025" for a local date ("2025-03-10"), in the user's own locale (when.ts's calendarDay). */
export function dayText(day: string, withYear = false): string {
  return calendarDay(day, { year: withYear })
}

/** The scrapbook to open first: the one Today points to, else the year so far, unless that is under a week old and
 * there is a year before it. */
export function firstKey(listing: ScrapbookListing | undefined): string | null {
  if (!listing?.periods.length) return null
  if (listing.featured) return listing.featured
  const [current, before] = listing.periods
  const days = (Date.parse(current.end) - Date.parse(current.start)) / 86_400_000
  return before && days < 7 ? before.key : current.key
}

/** Today's scrapbook card in an anniversary week or at New Year: "Our first year with Mira" and one stat, or null
 * on other days and once it was opened or put away. */
export function featuredCard(listing: ScrapbookListing | undefined, name: string): { key: string; title: string; stat: string } | null {
  const period = listing?.periods.find((item) => item.key === listing.featured)
  if (!period || !listing) return null
  const days = listing.featured_days
  return { key: period.key, title: period.key.startsWith('cal-') ? `${period.key.slice(4)} with ${name}` : `${period.title} with ${name}`, stat: `${days.toLocaleString('en-US')} ${days === 1 ? 'day' : 'days'} talked` }
}

/** A text page with little on it is set larger and centred. */
export function sparse(page: ScrapbookPage): boolean {
  if (page.kind === 'first' || page.kind === 'closing') return true
  return 'items' in page && page.items.length <= 2
}

/** Which page a swipe has reached, from how far the pages have scrolled. */
export function pageAt(scrollLeft: number, width: number, count: number): number {
  if (width <= 0) return 0
  return Math.min(count - 1, Math.max(0, Math.round(scrollLeft / width)))
}
