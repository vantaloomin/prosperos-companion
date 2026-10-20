import { calendarDay } from '../../when.ts'
import type { Occasion } from '../../types'

/** One line for Today: "Your birthday is in 3 days", "Tomorrow: Thanksgiving is always at their mom Ruth's…",
 * "It's been three months since you two started talking", "In 3 days it will be a year since you two swapped keys",
 * "It's a year today since Lena's mom Tracy died." */
export function occasionText(item: Occasion, name: string): string {
  const when = whenText(item.days)
  if (item.kind === 'user_birthday') return item.days === 0 ? 'Happy birthday! It is your birthday today.' : `Your birthday is ${when}.`
  if (item.kind === 'own_birthday' || item.kind === 'circle_birthday') return birthdayText(item, name, when)
  if (item.kind === 'tradition') return `${when.charAt(0).toUpperCase()}${when.slice(1)}: ${item.teaser ? `${item.teaser}.` : item.tradition}`
  if (item.kind === 'step_anniversary') return stepAnniversaryText(item, when)
  if (item.kind === 'death_anniversary') return `It's ${item.span} today since ${name}'s ${item.relation} ${item.person} died.`
  return `It's been ${item.span} since you two started talking.`
}

function whenText(days: number): string {
  return days === 0 ? 'today' : days === 1 ? 'tomorrow' : `in ${days} days`
}

/** Their birthday or a circle member's; a milestone (30, 40, 50 ...: companion/life/ages.py) says which: "It is
 * Dana's 40th birthday today." */
function birthdayText(item: Occasion, name: string, when: string): string {
  const big = item.turns ? `${ordinal(item.turns)} ` : ''
  const whose = item.kind === 'own_birthday' ? `${name}'s` : `${name}'s ${item.relation} ${item.person}'s`
  return `It is ${whose} ${big}birthday ${when}.`
}

/** Today's header lines: every occasion, but only the nearest step anniversary, which says how many more are due
 * ("and 3 more milestones this week"), so the header can't grow a line per step. */
export function headerOccasions(items: Occasion[], name: string): Array<{ key: string; text: string }> {
  const steps = items.filter((item) => item.kind === 'step_anniversary').sort((a, b) => a.days - b.days)
  const more = steps.length - 1
  return items.filter((item) => item.kind !== 'step_anniversary' || item === steps[0]).map((item) => {
    const text = occasionText(item, name)
    if (item !== steps[0] || more < 1) return { key: item.key, text }
    return { key: item.key, text: `${text.slice(0, -1)}, and ${more} more ${more === 1 ? 'milestone' : 'milestones'} this week.` }
  })
}

/** A step's anniversary (companion/life/steps.py): "It's been a year since you two became exclusive." */
function stepAnniversaryText(item: Occasion, when: string): string {
  if (item.days === 0) return `It's been ${item.span} since you two ${item.did}.`
  return `${when.charAt(0).toUpperCase()}${when.slice(1)} it will be ${item.span} since you two ${item.did}.`
}

/** "Mon, Oct 5" for a local date ("2026-10-05"), like every other date in the app (when.ts's calendarDay). */
export function storyDate(day: string): string {
  return calendarDay(day, { weekday: true })
}

export const DRAMA_LEVELS = [
  { value: 0, label: 'Quiet', hint: 'Good news now and then: a promotion, an engagement.' },
  { value: 1, label: 'Realistic', hint: 'Everyday ups and downs: a creepy new coworker, a friend’s breakup.' },
  { value: 2, label: 'Dramatic', hint: 'More often, and bigger: health scares, feuds, secret romances.' },
  { value: 3, label: 'Soap opera', hint: 'Drunk kisses, separations, family secrets.' },
] as const

/** 40th, 21st, 52nd. */
export function ordinal(value: number): string {
  const tens = value % 100
  const end = tens >= 10 && tens <= 20 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[value % 10] ?? 'th'
  return `${value}${end}`
}
