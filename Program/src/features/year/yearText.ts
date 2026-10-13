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

/** The key of the "All of it" view in the scrapbook's picker (Our history at a glance). */
export const ALL_OF_IT = 'all'
export const HISTORY_KEY = ['history']

/** A history line's stretch in the user's locale: "Week of Oct 5", "September 2026", "2025", or the span of quiet
 * ones in a row ("Oct 12 to Oct 25, 2026"). */
export function stretchText(line: { kind: 'week' | 'month' | 'year'; start: string; end: string; key: string }): string {
  const merged = line.kind === 'week' ? line.end > addDays(line.start, 6) : line.kind === 'month' ? line.start.slice(0, 7) !== line.end.slice(0, 7) : line.start.slice(0, 4) !== line.end.slice(0, 4)
  if (line.kind === 'year') return merged ? `${line.start.slice(0, 4)} to ${line.end.slice(0, 4)}` : line.start.slice(0, 4)
  if (line.kind === 'month') {
    const month = (day: string, withYear: boolean) => new Date(`${day.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString(undefined, { month: 'long', year: withYear ? 'numeric' : undefined, timeZone: 'UTC' })
    return merged ? `${month(line.start, line.start.slice(0, 4) !== line.end.slice(0, 4))} to ${month(line.end, true)}` : month(line.start, true)
  }
  return merged ? spanText(line.start, line.end) : `Week of ${dayText(line.key.slice(1))}`
}

/** History lines newest first, grouped by the year they start in, for the "All of it" view. */
export function byYear<T extends { start: string }>(lines: T[]): { year: string; lines: T[] }[] {
  const groups: { year: string; lines: T[] }[] = []
  for (const line of [...lines].reverse()) {
    const year = line.start.slice(0, 4)
    if (groups.at(-1)?.year === year) groups.at(-1)!.lines.push(line)
    else groups.push({ year, lines: [line] })
  }
  return groups
}

function addDays(day: string, days: number): string {
  const date = new Date(`${day.slice(0, 10)}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export type ScrapbookMode = 'years' | typeof ALL_OF_IT
const MODE_KEY = 'companion.scrapbook.view'

/** The scrapbook view the user last picked, remembered by this browser when it can. */
export function rememberedMode(): ScrapbookMode {
  try { return localStorage.getItem(MODE_KEY) === ALL_OF_IT ? ALL_OF_IT : 'years' } catch { return 'years' }
}

export function rememberMode(mode: ScrapbookMode) {
  try { localStorage.setItem(MODE_KEY, mode) } catch { /* private window: it is only a convenience */ }
}

/** The days talked beside a history line: "3 days", "1 day", or "No talking". */
export function daysText(days: number): string {
  return days ? `${days} ${days === 1 ? 'day' : 'days'}` : 'No talking'
}
