import { calendarDay } from '../../when.ts'
import type { Occasion, Storyline, YourPart } from '../../types'

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
  { value: 1, label: 'True to life', hint: 'Everyday ups and downs: a coworker taking credit, a friend’s breakup.' },
  { value: 2, label: 'Dramatic', hint: 'More often, and bigger: health scares, feuds, secret romances.' },
  { value: 3, label: 'Soap opera', hint: 'Drunk kisses, separations, family secrets.' },
] as const

/** The "Things that involve you" slider's steps (Settings > Realism, companion/life/shared_storylines.py). */
export const SHARED_STORY_LEVELS = [
  { label: 'Off', hint: 'Nothing they start draws you in. You still hear their news.' },
  { label: 'Now and then', hint: 'Every few weeks something comes up that includes you: a friend who wants to meet you, a favor, a place to show you.' },
  { label: 'True to life', hint: 'About once a week something comes up that includes you. Going, answering or letting it pass each lead somewhere different.' },
  { label: 'Often', hint: 'Something that includes you is nearly always under way, one at a time.' },
]

/** 40th, 21st, 52nd. */
export function ordinal(value: number): string {
  const tens = value % 100
  const end = tens >= 10 && tens <= 20 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[value % 10] ?? 'th'
  return `${value}${end}`
}

export const STORYLINES_KEY = ['storylines']

/** Today has two lists of storylines: the ones the user is part of ("Things that involve you") and the rest
 * ("Going on in their world"). */
export function withYou(items: Storyline[], involved: boolean): Storyline[] {
  return items.filter((item) => item.with_you === involved)
}

/** Where a storyline sits on Today, for the plan card's "See it". */
export function storylineAnchor(id: string): string {
  return `storyline-${id}`
}

const DID: Partial<Record<YourPart['did'], string>> = {
  answered: 'You wrote back.', said_yes: 'You said yes.', said_no: 'You said no.', dropped_by: 'You came by.',
  now: 'Happening now.', went: 'You went.', called_off: 'You called it off.',
}

/** The user's part in a beat, only from what the app knows for sure: "Mira texted you about it.", "You wrote back.",
 * "Set for Fri, Nov 20 at 7:00 PM.", "You went.", "You let it go by." Nothing for a beat they had no part in, or an
 * invitation that never went out. */
export function yourPart(you: YourPart | undefined, name: string, via: 'text' | 'plan' = 'text'): string {
  if (!you) return ''
  if (you.did === 'texted') return `${name.split(' ')[0]} texted you about it.`
  if (you.did === 'set') return you.on && you.at ? `Set for ${storyDate(you.on)} at ${clock(you.at)}.` : ''
  if (you.did === 'passed') return via === 'plan' ? '' : 'You let it go by.'
  return DID[you.did] ?? ''
}

/** "7:00 PM" from "19:00", kept on one line (as outingText's timeText). */
function clock(hhmm: string): string {
  const [hours, minutes] = hhmm.split(':').map(Number)
  return new Date(Date.UTC(2000, 0, 1, hours, minutes)).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' }).replace(/\s/gu, '\u00a0')
}
