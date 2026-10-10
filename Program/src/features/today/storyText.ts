import type { Occasion } from '../../types'

/** One line for Today: "Your birthday is in 3 days", "Tomorrow: Thanksgiving is always at their mom Ruth's…",
 * "It's been three months since you two started talking". */
export function occasionText(item: Occasion, name: string): string {
  const when = item.days === 0 ? 'today' : item.days === 1 ? 'tomorrow' : `in ${item.days} days`
  if (item.kind === 'user_birthday') return item.days === 0 ? 'Happy birthday! It is your birthday today.' : `Your birthday is ${when}.`
  if (item.kind === 'own_birthday') return `It is ${name}'s birthday ${when}.`
  if (item.kind === 'circle_birthday') return `It is ${name}'s ${item.relation} ${item.person}'s birthday ${when}.`
  if (item.kind === 'tradition') return `${when.charAt(0).toUpperCase()}${when.slice(1)}: ${item.teaser ?? item.tradition}`
  return `It's been ${item.span} since you two started talking.`
}

/** "Mon 5 Oct" for a local date ("2026-10-05"), without shifting it through a timezone. */
export function storyDate(day: string): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
}

export const DRAMA_LEVELS = [
  { value: 0, label: 'Quiet', hint: 'Good news now and then: a promotion, an engagement.' },
  { value: 1, label: 'Realistic', hint: 'Everyday ups and downs: a creepy new coworker, a friend’s breakup.' },
  { value: 2, label: 'Dramatic', hint: 'More often, and bigger: health scares, feuds, secret romances.' },
  { value: 3, label: 'Soap opera', hint: 'Drunk kisses, separations, family secrets.' },
] as const
