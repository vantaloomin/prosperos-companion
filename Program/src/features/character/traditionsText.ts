/** "Next: Thu 26 Nov" for a local date ("2026-11-26"), without shifting it through a timezone. */
export function nextText(day: string | null): string | null {
  if (!day) return null
  const [year, month, date] = day.split('-').map(Number)
  return `Next: ${new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })}`
}

/** "Up at home right now: a wreath on the front door and a carved pumpkin on the front step." */
export function decorationsText(items: string[]): string {
  const list = items.length > 1 ? `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}` : items[0]
  return `Up at home right now: ${list}.`
}
