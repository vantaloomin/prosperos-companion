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
