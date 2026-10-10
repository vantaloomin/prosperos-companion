import type { ScrapbookListing } from '../../types'

export const SCRAPBOOKS_KEY = ['scrapbooks']

/** "10 Mar 2025 to 9 Mar 2026" for a scrapbook's dates, without shifting them through a timezone. */
export function spanText(start: string, end: string): string {
  return `${dayText(start, true)} to ${dayText(end, true)}`
}

/** "10 Mar" or "10 Mar 2025" for a local date ("2025-03-10"). */
export function dayText(day: string, withYear = false): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: withYear ? 'numeric' : undefined, timeZone: 'UTC' })
}

/** The scrapbook to open first: the one Today points to, else the year so far. */
export function firstKey(listing: ScrapbookListing | undefined): string | null {
  if (!listing?.periods.length) return null
  return listing.featured ?? listing.periods[0].key
}

/** Today's line on an anniversary or at New Year, or null on other days. */
export function featuredText(listing: ScrapbookListing | undefined, name: string): string | null {
  const period = listing?.periods.find((item) => item.key === listing.featured)
  if (!period) return null
  return period.key.startsWith('cal-') ? `${period.title}: a look back at your year with ${name} is ready.` : `${period.title} with ${name}: your scrapbook is ready.`
}

/** Which page a swipe has reached, from how far the pages have scrolled. */
export function pageAt(scrollLeft: number, width: number, count: number): number {
  if (width <= 0) return 0
  return Math.min(count - 1, Math.max(0, Math.round(scrollLeft / width)))
}
